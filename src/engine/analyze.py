import logging
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.express as px
from jinja2 import Environment, FileSystemLoader

from src.parsers.perf_stat_timeseries_parser import parse_perf_stat_timeseries
from src.parsers.sar_timeseries_parser import parse_sar_timeseries

log = logging.getLogger(__name__)


def run_analysis_poc(level_dir: Path, html_report_path: Optional[Path] = None):
    """
    Runs the PoC for data alignment and optionally generates an HTML report.
    :param level_dir: The path to a specific level directory (e.g., 'intensity_8')
                      containing the collector output files.
    """
    log.info(f"--- Running Analysis PoC on directory: {level_dir} ---")

    perf_file = level_dir / "perf_stat.txt"
    sar_file = level_dir / "sar_cpu.txt"

    if not perf_file.exists() or not sar_file.exists():
        log.error(f"Missing required data files in {level_dir}. Aborting PoC.")
        return

    log.info("Parsing perf_stat and sar data...")
    perf_content = perf_file.read_text()
    sar_content = sar_file.read_text()

    df_perf_raw = parse_perf_stat_timeseries(perf_content)
    results_sar = parse_sar_timeseries(sar_content)

    df_sar_cpu = results_sar.get("cpu")
    if df_sar_cpu is None or df_sar_cpu.empty:
        log.error("CPU data block not found or is empty in sar output. Aborting PoC.")
        return
    df_sar = df_sar_cpu[df_sar_cpu["CPU"] == "all"].copy()

    if df_perf_raw.empty or df_sar.empty:
        log.error("Parsing resulted in empty DataFrames. Aborting PoC.")
        return

    df_perf = df_perf_raw.pivot(index="timestamp", columns="event_name", values="value").reset_index()
    log.info("Pivoted perf DataFrame for alignment.")

    df_perf = df_perf.sort_values("timestamp")
    df_sar = df_sar.sort_values("timestamp")

    log.info("Performing as-of merge...")
    df_sar["timestamp_dt"] = pd.to_datetime(df_sar["timestamp"].astype(str), format="%H:%M:%S")
    df_sar["timestamp_float"] = (df_sar["timestamp_dt"] - df_sar["timestamp_dt"].iloc[0]).dt.total_seconds()

    merged_df = pd.merge_asof(
        left=df_sar,
        right=df_perf,
        left_on="timestamp_float",
        right_on="timestamp",
        direction="nearest",
    )

    log.info("--- Analysis PoC Complete. ---")
    columns_to_drop = ["timestamp_dt", "timestamp_float", "CPU"]
    merged_df.drop(columns=[col for col in columns_to_drop if col in merged_df.columns], inplace=True)

    if html_report_path:
        log.info("Generating interactive plot...")
        fig = px.line(
            merged_df,
            x="timestamp_x",
            y=["pct_usr", "instructions:u"],
            title="CPU Utilization vs Instructions Over Time",
            labels={"timestamp_x": "Time", "value": "Metric Value", "variable": "Metric"},
        )
        plot_div = fig.to_html(full_html=False, include_plotlyjs="cdn")

        log.info(f"Generating HTML report at: {html_report_path}")
        env = Environment(loader=FileSystemLoader("src/templates"))
        template = env.get_template("report_template.html")
        html_content = template.render(
            interactive_plot=plot_div,
            aligned_table=merged_df.to_html(index=False, classes="table", border=0),
        )
        with open(html_report_path, "w") as f:
            f.write(html_content)
        log.info("✅ HTML report with interactive plot generated successfully.")

    return merged_df
