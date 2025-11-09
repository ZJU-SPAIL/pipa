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
        if name == "perf_raw":
            continue

        if df.empty:
            continue

        log.info(f"Processing data for '{name}'...")

        tables[name] = df.round(2).to_json(orient="records")
        log.info(f"Generated data table for '{name}'.")

        try:
            time_col = None
            if "timestamp" in df.columns:
                time_col = "timestamp"

            if not time_col:
                continue

            id_col = None
            for col in ["CPU", "IFACE", "DEV"]:
                if col in df.columns:
                    id_col = col
                    break

            value_cols = [
                c
                for c in df.columns
                if df[c].dtype in ["int64", "float64", "int32", "float32"] and c not in ["interval", "hostname"]
            ]

            if not value_cols:
                continue

            if id_col:
                fig = px.line(
                    df,
                    x=time_col,
                    y=value_cols,
                    color=id_col,
                    title=f"{name.replace('_', ' ').title()} Metrics",
                )
            else:
                fig = px.line(
                    df,
                    x=time_col,
                    y=value_cols,
                    title=f"{name.replace('_', ' ').title()} Metrics",
                )

            fig.update_layout(autosize=True, height=500, legend_itemclick="toggle")
            plots[name] = fig.to_html(full_html=False, include_plotlyjs="cdn")
            log.info(f"Generated plot for '{name}'.")
        except Exception as e:
            log.warning(f"Could not generate plot for '{name}': {e}")

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
    )
    with open(report_path, "w") as f:
        f.write(html_content)
    log.info("✅ HTML report generation complete.")

    return None
