import logging
from pathlib import Path

import pandas as pd
import plotly.express as px
import yaml
from jinja2 import Environment, FileSystemLoader
from markdown_it import MarkdownIt

from src.engine.rules import calculate_context_metrics, format_rules_to_html_tree, load_rules, run_rules_engine
from src.parsers.perf_stat_timeseries_parser import parse_perf_stat_timeseries
from src.utils import get_project_root

log = logging.getLogger(__name__)


def generate_report(level_dir: Path, report_path: Path):
    """
    Analyzes all available sampling data (perf, multi-sar) and generates a comprehensive
    self-contained HTML report.
    """
    log.info(f"--- Generating analysis report from directory: {level_dir} ---")

    analysis_warnings = []
    all_dataframes = {}

    static_info_str, static_info_data = "", {}
    try:
        static_info_path = level_dir.parent / "static_info.yaml"
        with open(static_info_path, "r") as f:
            static_info_data = yaml.safe_load(f)
            static_info_str = yaml.dump(static_info_data, indent=2, allow_unicode=True)
        log.info(f"Loaded static system info from {static_info_path.name}.")
    except FileNotFoundError:
        analysis_warnings.append("static_info.yaml not found. The report will lack system context.")

    df_perf_raw = pd.DataFrame()
    try:
        perf_content = (level_dir / "perf_stat.txt").read_text()
        if perf_content:
            df_perf_raw = parse_perf_stat_timeseries(perf_content)
            all_dataframes["perf_raw"] = df_perf_raw
            log.info("Successfully parsed perf_stat.txt.")
        else:
            analysis_warnings.append("perf_stat.txt is empty.")
    except FileNotFoundError:
        analysis_warnings.append("perf_stat.txt not found. Perf-related analysis will be skipped.")

    if not (level_dir / "perf.data").exists():
        analysis_warnings.append("perf.data not found. Flame graph generation will not be possible.")

    log.info("Dynamically loading all available SAR data files...")
    sar_files = sorted(level_dir.glob("sar_*.csv"))
    if not sar_files:
        analysis_warnings.append("No sar_*.csv files found.")
    else:
        for sar_csv_path in sar_files:
            metric_name = sar_csv_path.stem.split("sar_")[1]
            try:
                if sar_csv_path.stat().st_size > 0:
                    with open(sar_csv_path, "r") as f:
                        lines = f.readlines()

                    header_line = None
                    data_start_idx = 0
                    for i, line in enumerate(lines):
                        if line.startswith("#"):
                            header_line = line[1:].strip()
                            data_start_idx = i + 1
                            break

                    if header_line:
                        from io import StringIO

                        csv_content = header_line + "\n" + "".join(lines[data_start_idx:])
                        df_sar = pd.read_csv(StringIO(csv_content), sep=";")
                    else:
                        df_sar = pd.read_csv(sar_csv_path, sep=";")

                    if not df_sar.empty:
                        if "CPU" in df_sar.columns:
                            df_sar["CPU"] = df_sar["CPU"].astype(str)
                            df_sar.loc[df_sar["CPU"] == "-1", "CPU"] = "all"

                        all_dataframes[f"sar_{metric_name}"] = df_sar
                        log.info(f"Successfully loaded and processed {sar_csv_path.name}.")
            except Exception as e:
                analysis_warnings.append(f"Failed to process {sar_csv_path.name}: {e}")

    project_root = get_project_root()
    rules_path = project_root / "config/rules/decision_tree.yaml"
    rules, rule_configs = load_rules(rules_path)
    context = calculate_context_metrics(all_dataframes, static_info_data)
    context.update(rule_configs)
    findings = run_rules_engine(all_dataframes, rules, context)
    md = MarkdownIt()
    decision_tree_html, findings_for_tree_html = format_rules_to_html_tree(rules, all_dataframes, context, md)

    plots = {}
    tables = {}

    if "perf_raw" in all_dataframes and not all_dataframes["perf_raw"].empty:
        df_perf = (
            all_dataframes["perf_raw"]
            .pivot_table(index=["timestamp", "cpu"], columns="event_name", values="value")
            .reset_index()
        )
        all_dataframes["perf"] = df_perf

    for name, df in all_dataframes.items():
        if name == "perf_raw" or df.empty:
            continue

        log.info(f"Processing data for '{name}'...")
        tables[name] = df.round(2).to_json(orient="records")

        try:
            time_col = "timestamp"
            if time_col not in df.columns:
                continue

            if name == "sar_cpu":
                id_col = "CPU"
                if "%user" in df.columns and "%system" in df.columns:
                    df["%total"] = df["%user"] + df["%system"]

                metrics_to_plot = [m for m in ["%user", "%system", "%iowait", "%idle", "%total"] if m in df.columns]

                melted_df = df.melt(
                    id_vars=[time_col, "CPU"],
                    value_vars=metrics_to_plot,
                    var_name="metric",
                    value_name="utilization",
                )

                fig = px.line(
                    melted_df,
                    x=time_col,
                    y="utilization",
                    color="CPU",
                    line_dash="metric",
                    title="Sar CPU Metrics (Per-Core & Overall)",
                    labels={"utilization": "CPU Utilization (%)"},
                )
                fig.update_layout(
                    height=600,
                    showlegend=True,
                    legend=dict(
                        title="Metrics",
                        orientation="v",
                        yanchor="top",
                        y=1.0,
                        xanchor="left",
                        x=1.01,
                        bgcolor="rgba(255,255,255,0.8)",
                        bordercolor="rgba(0,0,0,0.2)",
                        borderwidth=1,
                    ),
                    margin=dict(r=200),
                )

                plots[name] = fig.to_html(full_html=False, include_plotlyjs="cdn")

                filter_options = {"CPU": sorted(df["CPU"].unique().tolist()), "METRIC": metrics_to_plot}

                filters_with_hints = {}
                for key, values in filter_options.items():
                    source_property = "legendgroup" if key == "CPU" else "name"
                    filters_with_hints[key] = {
                        "values": values,
                        "sample": values[:3],
                        "count": len(values),
                        "source": source_property,
                    }
                context[f"{name}_filters"] = filters_with_hints

            else:
                percent_cols = [c for c in df.columns if "%" in c and df[c].dtype.kind in "if"]
                absolute_cols = [
                    c
                    for c in df.columns
                    if df[c].dtype.kind in "if" and c not in percent_cols and c not in ["interval", "hostname"]
                ]

                id_col = next((col for col in ["IFACE", "DEV", "cpu"] if col in df.columns), None)

                metric_groups = {}
                if percent_cols:
                    metric_groups["percent"] = percent_cols
                if absolute_cols:
                    metric_groups["absolute"] = absolute_cols

                for metric_type, cols_to_plot in metric_groups.items():
                    if not cols_to_plot:
                        continue

                    plot_name = f"{name}_{metric_type}" if len(metric_groups) > 1 else name
                    melted_df = df.melt(
                        id_vars=[time_col] + ([id_col] if id_col else []),
                        value_vars=cols_to_plot,
                        var_name="metric",
                        value_name="value",
                    )
                    if melted_df.empty:
                        continue

                    chart_title = f"{name.replace('_', ' ').title()} Metrics"
                    y_axis_title = "Value"
                    if name == "sar_load":
                        chart_title = "System Load & Run Queue Length"
                    if metric_type == "percent":
                        y_axis_title = "Percentage (%)"
                        if len(metric_groups) > 1:
                            chart_title += " (Percentages)"
                    elif len(metric_groups) > 1:
                        chart_title += " (Absolute Values)"

                    fig = px.line(
                        melted_df,
                        x=time_col,
                        y="value",
                        color="metric",
                        line_dash=id_col,
                        title=chart_title,
                        labels={"value": y_axis_title},
                    )

                    fig.update_layout(
                        height=500,
                        showlegend=True,
                        legend=dict(
                            title="Metrics",
                            orientation="v",
                            yanchor="top",
                            y=1.0,
                            xanchor="left",
                            x=1.01,
                            bgcolor="rgba(255,255,255,0.8)",
                            bordercolor="rgba(0,0,0,0.2)",
                            borderwidth=1,
                        ),
                        margin=dict(r=200),
                    )

                    plots[plot_name] = fig.to_html(full_html=False, include_plotlyjs="cdn")

                    filter_options = {"METRIC": sorted(cols_to_plot)}
                    if id_col:
                        filter_options[id_col] = sorted(df[id_col].unique().tolist())

                    if filter_options:
                        filters_with_hints = {}
                        for key, values in filter_options.items():
                            source_property = "legendgroup" if (id_col and key == id_col) else "name"
                            filters_with_hints[key] = {
                                "values": values,
                                "sample": values[:3],
                                "count": len(values),
                                "source": source_property,
                            }
                        context[f"{plot_name}_filters"] = filters_with_hints
        except Exception as e:
            log.warning(f"Could not generate plot for '{name}': {e}", exc_info=True)

    log.info(f"Generating HTML report at: {report_path}")
    templates_dir = get_project_root() / "src/templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    env.filters["markdown"] = lambda text: md.render(text)

    template = env.get_template("report_template.html")
    html_content = template.render(
        warnings=analysis_warnings,
        plots=plots,
        tables_json=tables,
        findings=findings,
        decision_tree_html=decision_tree_html,
        findings_for_tree_html=findings_for_tree_html,
        static_info_str=static_info_str,
        static_info_data=static_info_data,
        context=context,
    )
    with open(report_path, "w") as f:
        f.write(html_content)
    log.info("✅ HTML report generation complete.")

    return None
