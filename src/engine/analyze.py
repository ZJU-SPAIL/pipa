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
    Analyzes sampling data, generates insights and interactive plots, and creates a
    self-contained HTML report. Handles missing data files gracefully.
    """
    log.info(f"--- Generating analysis report from directory: {level_dir} ---")

    analysis_warnings = []

    static_info_str = ""
    static_info_path = level_dir.parent / "static_info.yaml"
    static_info_data = {}
    try:
        with open(static_info_path, "r") as f:
            static_info_data = yaml.safe_load(f)
            static_info_str = yaml.dump(static_info_data, indent=2, allow_unicode=True)
            log.info(f"Loaded static system info from {static_info_path.name}.")
    except FileNotFoundError:
        warning = "static_info.yaml not found. The report will lack system context."
        log.warning(warning)
        analysis_warnings.append(warning)

    df_perf_raw = pd.DataFrame()
    try:
        perf_content = (level_dir / "perf_stat.txt").read_text()
        if perf_content:
            df_perf_raw = parse_perf_stat_timeseries(perf_content)
            log.info("Successfully parsed perf_stat.txt.")
        else:
            analysis_warnings.append("perf_stat.txt is empty.")
    except FileNotFoundError:
        analysis_warnings.append("perf_stat.txt not found. Perf-related analysis will be skipped.")
    perf_data_path = level_dir / "perf.data"
    if not perf_data_path.exists():
        analysis_warnings.append("perf.data not found. Flame graph generation will not be possible for this snapshot.")
    df_sar = pd.DataFrame()
    try:
        sar_csv_path = level_dir / "sar_cpu.csv"
        if sar_csv_path.exists() and sar_csv_path.stat().st_size > 0:
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

            log.info(f"Successfully loaded sar data from {sar_csv_path.name}.")

            if "CPU" in df_sar.columns:
                df_sar["CPU"] = df_sar["CPU"].astype(str)
                df_sar.loc[df_sar["CPU"] == "-1", "CPU"] = "all"

        else:
            analysis_warnings.append("sar_cpu.csv not found or is empty.")
    except Exception as e:
        warning = f"Failed to read or process sar_cpu.csv: {e}"
        log.error(warning, exc_info=True)
        analysis_warnings.append(warning)

    results_sar = {"cpu": df_sar} if not df_sar.empty else {}

    df_sar_all_cpu = pd.DataFrame()
    df_sar_per_core = pd.DataFrame()

    if not df_sar.empty and "CPU" in df_sar.columns:
        log.debug(f"SAR DataFrame shape: {df_sar.shape}")
        log.debug(f"SAR CPU unique values: {df_sar['CPU'].unique()}")
        df_sar_all_cpu = df_sar[df_sar["CPU"] == "all"].copy()
        df_sar_per_core = df_sar[df_sar["CPU"] != "all"].copy()
        log.debug(f"df_sar_all_cpu shape: {df_sar_all_cpu.shape}, df_sar_per_core shape: {df_sar_per_core.shape}")

    df_perf = pd.DataFrame()
    if not df_perf_raw.empty:
        df_perf = df_perf_raw.pivot_table(
            index=["timestamp", "cpu"], columns="event_name", values="value"
        ).reset_index()

    all_dataframes = {"perf_raw": df_perf_raw, "perf": df_perf, **results_sar}
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
    md = MarkdownIt()

    if not df_sar_all_cpu.empty:
        log.info("Generating plot and table for SAR (all-cpu) data...")

        id_vars = ["timestamp", "hostname", "CPU"]
        value_vars = [col for col in df_sar_all_cpu.columns if col not in id_vars]

        df_sar_all_cpu_long = df_sar_all_cpu.melt(
            id_vars=id_vars, value_vars=value_vars, var_name="metric", value_name="value"
        )

        if "timestamp" in df_sar_all_cpu_long.columns:
            fig_sar = px.line(
                df_sar_all_cpu_long,
                x="timestamp",
                y="value",
                color="metric",
                title="SAR CPU Metrics (Overall)",
            )
            fig_sar.update_layout(autosize=True, height=500, legend_itemclick="toggle")
            plots["sar_cpu_all"] = fig_sar.to_html(full_html=False, include_plotlyjs="cdn")

        tables["sar_cpu"] = df_sar_all_cpu.round(2).to_json(orient="records")

    if not df_sar_per_core.empty:
        log.info("Generating plot for Per-Core SAR data...")

        df_sar_per_core_plot = df_sar_per_core.copy()
        df_sar_per_core_plot["%total"] = df_sar_per_core_plot["%user"] + df_sar_per_core_plot["%system"]

        id_vars = ["timestamp", "hostname", "CPU"]
        value_vars = ["%user", "%system", "%total"]
        df_sar_per_core_long = df_sar_per_core_plot.melt(
            id_vars=id_vars, value_vars=value_vars, var_name="metric", value_name="value"
        )

        df_sar_per_core_long["CPU_Metric"] = (
            df_sar_per_core_long["CPU"].astype(str) + " - " + df_sar_per_core_long["metric"]
        )

        fig_sar_per_core = px.line(
            df_sar_per_core_long,
            x="timestamp",
            y="value",
            color="CPU_Metric",
            title="Per-Core CPU Utilization (%)",
            labels={"value": "Utilization (%)"},
        )

        all_traces = df_sar_per_core_long["CPU_Metric"].unique().tolist()
        user_traces = [t for t in all_traces if "%user" in t]
        system_traces = [t for t in all_traces if "%system" in t]
        total_traces = [t for t in all_traces if "%total" in t]

        fig_sar_per_core.update_layout(
            autosize=True,
            height=500,
            legend_title_text="CPU Core - Metric",
            updatemenus=[
                dict(
                    buttons=list(
                        [
                            dict(args=[{"visible": [True] * len(all_traces)}], label="Show All", method="update"),
                            dict(args=[{"visible": [False] * len(all_traces)}], label="Hide All", method="update"),
                            dict(
                                args=[{"visible": [t in user_traces for t in all_traces]}],
                                label="Show %user only",
                                method="update",
                            ),
                            dict(
                                args=[{"visible": [t in system_traces for t in all_traces]}],
                                label="Show %system only",
                                method="update",
                            ),
                            dict(
                                args=[{"visible": [t in total_traces for t in all_traces]}],
                                label="Show %total only",
                                method="update",
                            ),
                        ]
                    ),
                    direction="down",
                    pad={"r": 10, "t": 10},
                    showactive=True,
                    x=0.0,
                    xanchor="left",
                    y=1.15,
                    yanchor="top",
                ),
            ],
        )
        plots["sar_per_core"] = fig_sar_per_core.to_html(full_html=False, include_plotlyjs="cdn")

    if not df_perf.empty:
        log.info("Generating plot and table for Perf data...")
        perf_cols_to_plot = [col for col in df_perf.columns if col not in ["timestamp", "cpu"]]
        if "timestamp" in df_perf.columns and perf_cols_to_plot:
            fig_perf = px.line(df_perf, x="timestamp", y=perf_cols_to_plot, title="Perf Micro-Architectural Metrics")
            fig_perf.update_layout(autosize=True, height=500, legend_itemclick="toggle")
            plots["perf_stat"] = fig_perf.to_html(full_html=False, include_plotlyjs="cdn")
        tables["perf_stat"] = df_perf.round(2).to_json(orient="records")

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
    )
    with open(report_path, "w") as f:
        f.write(html_content)
    log.info("✅ HTML report generation complete.")

    return None
