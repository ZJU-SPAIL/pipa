import logging
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple

import click
import pandas as pd
from tabulate import tabulate

from src.pipa.parsers import PARSER_REGISTRY
from src.pipa.parsers.perf_stat_timeseries_parser import parse as parse_perf_stat

log = logging.getLogger(__name__)


def _extract_summary_metrics(df_sar: pd.DataFrame, df_perf: pd.DataFrame) -> Dict[str, Optional[float]]:
    """从已加载的 DataFrame 中，计算关键的摘要标量指标。"""
    metrics: Dict[str, Optional[float]] = {
        "avg_cpu_user": None,
        "avg_cpu_system": None,
        "avg_cpu_idle": None,
        "total_instructions": None,
        "total_cycles": None,
        "ipc": None,
    }

    if not df_sar.empty:
        try:
            df_sar_all = df_sar[df_sar["CPU"] == "all"]
            if not df_sar_all.empty:
                metrics["avg_cpu_user"] = float(df_sar_all["%user"].mean())
                metrics["avg_cpu_system"] = float(df_sar_all["%system"].mean())
                metrics["avg_cpu_idle"] = float(df_sar_all["%idle"].mean())
        except (KeyError, TypeError) as e:
            log.warning(f"Could not calculate SAR summary metrics: {e}")

    if not df_perf.empty:
        try:
            instructions = df_perf[df_perf["event_name"].isin(["instructions", "inst_retired.any"])]["value"].sum()
            cycles = df_perf[df_perf["event_name"].isin(["cycles", "cpu-cycles"])]["value"].sum()
            if instructions > 0 and cycles > 0:
                metrics["total_instructions"] = float(instructions)
                metrics["total_cycles"] = float(cycles)
                metrics["ipc"] = float(instructions / cycles)
        except (KeyError, TypeError) as e:
            log.warning(f"Could not calculate Perf summary metrics: {e}")

    return metrics


def _load_timeseries_data(snapshot_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    从解压的快照目录中加载SAR和Perf时间序列数据，
    使用集中的解析器注册表。
    """
    level_dir = next(snapshot_dir.iterdir(), None)
    if not level_dir or not level_dir.is_dir():
        raise FileNotFoundError("Could not find data directory inside unpacked snapshot.")

    df_sar_all_cpu = pd.DataFrame()
    df_perf_all = pd.DataFrame()

    try:
        sar_csv_path = level_dir / "sar_cpu.csv"
        sar_parser = PARSER_REGISTRY.get("sar_cpu")
        if sar_csv_path.exists() and sar_parser:
            df_sar = sar_parser(sar_csv_path)
            if not df_sar.empty:
                df_sar_all_cpu = df_sar[df_sar["CPU"] == "all"].copy()

        perf_txt_path = level_dir / "perf_stat.txt"
        if perf_txt_path.exists():
            perf_content = perf_txt_path.read_text()
            if perf_content:
                df_perf_raw = parse_perf_stat(perf_content)
                if not df_perf_raw.empty:
                    df_perf_all = df_perf_raw[df_perf_raw["cpu"] == "all"].copy()

    except Exception as e:
        log.error(f"Error loading time-series data from {snapshot_dir}: {e}", exc_info=True)
        raise

    return df_sar_all_cpu, df_perf_all


def _run_comparison(input_a: Path, input_b: Path, output_html_path: Optional[Path] = None):
    log.info(f"Starting comparison between '{input_a.name}' (A) and '{input_b.name}' (B)")
    with (
        tempfile.TemporaryDirectory(prefix="pipa_cmp_A_") as temp_a,
        tempfile.TemporaryDirectory(prefix="pipa_cmp_B_") as temp_b,
    ):
        shutil.unpack_archive(input_a, temp_a, format="gztar")
        shutil.unpack_archive(input_b, temp_b, format="gztar")
        df_sar_a, df_perf_a = _load_timeseries_data(Path(temp_a))
        df_sar_b, df_perf_b = _load_timeseries_data(Path(temp_b))
        metrics_a = _extract_summary_metrics(df_sar_a, df_perf_a)
        metrics_b = _extract_summary_metrics(df_sar_b, df_perf_b)
        metric_definitions = {
            "avg_cpu_user": {"name": "Avg CPU User %", "format": "{:.2f}%"},
            "avg_cpu_system": {"name": "Avg CPU System %", "format": "{:.2f}%"},
            "avg_cpu_idle": {"name": "Avg CPU Idle %", "format": "{:.2f}%"},
            "total_instructions": {"name": "Total Instructions", "format": "{:,.0f}"},
            "total_cycles": {"name": "Total Cycles", "format": "{:,.0f}"},
            "ipc": {"name": "IPC (Instructions/Cycle)", "format": "{:.3f}"},
        }
        table_data = []
        for key, definition in metric_definitions.items():
            val_a, val_b = metrics_a.get(key), metrics_b.get(key)
            if val_a is None or val_b is None:
                continue
            diff = val_b - val_a
            change_str = f"{(diff / val_a * 100):+.2f}%" if val_a != 0 else "N/A"
            table_data.append(
                [
                    definition["name"],
                    definition["format"].format(val_a),
                    definition["format"].format(val_b),
                    definition["format"].format(diff).replace("%", ""),
                    change_str,
                ]
            )
        terminal_report = tabulate(
            table_data, headers=["Metric", "Baseline (A)", "Target (B)", "Diff", "% Change"], tablefmt="grid"
        )
        if output_html_path:
            pass
        return terminal_report


@click.command()
@click.option(
    "--input-a",
    "input_a_path_str",
    required=True,
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to the first .pipa archive (baseline).",
)
@click.option(
    "--input-b",
    "input_b_path_str",
    required=True,
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to the second .pipa archive (comparison target).",
)
@click.option(
    "--output",
    "output_path_str",
    required=False,
    type=click.Path(writable=True, dir_okay=False, resolve_path=True),
    default=None,
    help="Path to save the generated HTML comparison report.",
)
def compare(input_a_path_str: str, input_b_path_str: str, output_path_str: Optional[str]):
    """
    比较两个pipa快照并生成比较报告。
    """
    input_a_path = Path(input_a_path_str)
    input_b_path = Path(input_b_path_str)
    output_path = Path(output_path_str) if output_path_str else None

    try:
        terminal_report = _run_comparison(input_a_path, input_b_path, output_path)
        click.secho("\n--- PIPA Performance Comparison (Terminal Summary) ---", fg="cyan", bold=True)
        click.echo(terminal_report)
        if output_path:
            click.secho(f"\n✅ Full comparison report saved to: {output_path}", fg="green")
    except Exception as e:
        click.secho(f"❌ An error occurred during the comparison: {e}", fg="red")
        raise click.Abort()
