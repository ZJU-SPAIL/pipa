import logging
from pathlib import Path

import pandas as pd

from src.parsers.perf_stat_timeseries_parser import parse_perf_stat_timeseries
from src.parsers.sar_timeseries_parser import parse_sar_timeseries

log = logging.getLogger(__name__)


def run_analysis_poc(level_dir: Path):
    """
    Runs the Proof of Concept for time-series data alignment.
    运行一个时序数据对齐的 PoC (Proof of Concept)。

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

    log.info("--- Analysis PoC Complete. Returning merged DataFrame. ---")
    return merged_df
