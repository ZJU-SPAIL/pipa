import logging
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import yaml
from jinja2 import Environment, FileSystemLoader
from markdown_it import MarkdownIt

from src.engine.rules import calculate_context_metrics, format_rules_to_html_tree, load_rules, run_rules_engine
from src.parsers.perf_stat_timeseries_parser import parse_perf_stat_timeseries
from src.parsers.sar_timeseries_parser import parse_sar_timeseries
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

    results_sar = {}
    try:
        sar_content = (level_dir / "sar_cpu.txt").read_text()
        if sar_content:
            results_sar = parse_sar_timeseries(sar_content)
            log.info("Successfully parsed sar_cpu.txt.")
        else:
            analysis_warnings.append("sar_cpu.txt is empty.")
    except FileNotFoundError:
        analysis_warnings.append("sar_cpu.txt not found. SAR-related analysis will be skipped.")

    df_sar = results_sar.get("cpu", pd.DataFrame())
    if not df_sar.empty:
        df_sar = df_sar[df_sar["CPU"] == "all"].copy()

    df_perf = pd.DataFrame()
    if not df_perf_raw.empty:
        df_perf = df_perf_raw.pivot(index="timestamp", columns="event_name", values="value").reset_index()

    merged_df = pd.DataFrame()
    if not df_sar.empty and not df_perf.empty:
        log.info("Both SAR and Perf data available. Performing as-of merge...")
        df_perf = df_perf.sort_values("timestamp")
        df_sar = df_sar.sort_values("timestamp")

        df_sar["timestamp_dt"] = pd.to_datetime(
            df_sar["timestamp"].astype(str), format="%H:%M:%S", errors="coerce"
        ).dt.time

        df_sar["sar_abs_seconds"] = df_sar["timestamp_dt"].apply(
            lambda t: t.hour * 3600 + t.minute * 60 + t.second if pd.notnull(t) else None
        )

        sar_start_time = df_sar["sar_abs_seconds"].iloc[0]
        df_sar["relative_seconds"] = df_sar["sar_abs_seconds"] - sar_start_time
        df_sar["relative_seconds"] = df_sar["relative_seconds"].astype(float)
        perf_start_time = df_perf["timestamp"].iloc[0]
        df_perf["relative_seconds"] = df_perf["timestamp"] - perf_start_time

        merged_df = pd.merge_asof(
            left=df_sar.sort_values("relative_seconds"),
            right=df_perf.sort_values("relative_seconds"),
            on="relative_seconds",
            direction="backward",
        )
        if "timestamp_y" in merged_df.columns:
            merged_df.rename(columns={"timestamp_x": "sar_timestamp", "timestamp_y": "perf_timestamp"}, inplace=True)
        else:
            merged_df.rename(columns={"timestamp": "sar_timestamp"}, inplace=True)

    elif not df_sar.empty:
        log.info("Only SAR data available. Using it as the primary timeseries data.")
        merged_df = df_sar
        merged_df.rename(columns={"timestamp": "sar_timestamp"}, inplace=True)
    elif not df_perf.empty:
        log.info("Only Perf data available. Using it as the primary timeseries data.")
        merged_df = df_perf
        merged_df.rename(columns={"timestamp": "perf_timestamp"}, inplace=True)
    else:
        log.warning("No time-series data available to generate plots or tables.")

    all_dataframes = {"perf": df_perf, **results_sar}
    project_root = get_project_root()
    rules_path = project_root / "config/rules/decision_tree.yaml"
    rules = load_rules(rules_path)
    context = calculate_context_metrics(all_dataframes, static_info_data)
    findings = run_rules_engine(all_dataframes, rules, context)
    md = MarkdownIt()
    decision_tree_html, findings_for_tree_html = format_rules_to_html_tree(rules, all_dataframes, context, md)

    plot_div = ""
    table_json_data = "[]"
    if not merged_df.empty:
        log.info("Generating interactive plot and data table...")
        columns_to_plot = [
            col for col in merged_df.columns if pd.api.types.is_numeric_dtype(merged_df[col]) and "timestamp" not in col
        ]
        if columns_to_plot:
            timestamp_col = next((c for c in ["timestamp_x", "timestamp"] if c in merged_df.columns), None)
            if timestamp_col:
                fig = px.line(
                    merged_df,
                    x=timestamp_col,
                    y=columns_to_plot,
                    title="Time-Series Metrics Explorer",
                    labels={timestamp_col: "Time", "value": "Metric Value", "variable": "Metric"},
                )
                fig.update_layout(autosize=True, height=600, legend_itemclick="toggleothers")
                plot_div = fig.to_html(full_html=False, include_plotlyjs="cdn")

        df_for_table = merged_df.round(2).replace([np.inf, -np.inf], "Infinity").fillna("N/A")
        table_json_data = df_for_table.to_json(orient="records")

    log.info(f"Generating HTML report at: {report_path}")
    env = Environment(loader=FileSystemLoader("src/templates"))
    env.filters["markdown"] = lambda text: md.render(text)

    template = env.get_template("report_template.html")
    html_content = template.render(
        warnings=analysis_warnings,
        interactive_plot=plot_div,
        table_data_json=table_json_data,
        findings=findings,
        decision_tree_html=decision_tree_html,
        findings_for_tree_html=findings_for_tree_html,
        static_info_str=static_info_str,
    )
    with open(report_path, "w") as f:
        f.write(html_content)
    log.info("✅ HTML report generation complete.")

    return merged_df
