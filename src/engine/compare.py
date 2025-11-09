import logging
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd
import plotly.express as px
from jinja2 import Environment, FileSystemLoader
from tabulate import tabulate

from src.parsers.perf_stat_timeseries_parser import parse_perf_stat_timeseries
from src.utils import get_project_root

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
            metrics["avg_cpu_user"] = float(df_sar["%user"].mean())
            metrics["avg_cpu_system"] = float(df_sar["%system"].mean())
            metrics["avg_cpu_idle"] = float(df_sar["%idle"].mean())
            log.debug(
                f"SAR metrics: user={metrics['avg_cpu_user']:.2f}, "
                f"system={metrics['avg_cpu_system']:.2f}, idle={metrics['avg_cpu_idle']:.2f}"
            )
        except (KeyError, TypeError) as e:
            log.warning(f"Could not calculate SAR summary metrics: {e}")
    else:
        log.debug("SAR DataFrame is empty, skipping SAR metrics")

    if not df_perf.empty:
        try:
            instructions = df_perf[df_perf["event_name"].isin(["instructions", "inst_retired.any"])]["value"].sum()
            cycles = df_perf[df_perf["event_name"].isin(["cycles", "cpu-cycles"])]["value"].sum()
            if instructions > 0 and cycles > 0:
                metrics["total_instructions"] = float(instructions)
                metrics["total_cycles"] = float(cycles)
                metrics["ipc"] = float(instructions / cycles)
                msg = f"Perf: inst={instructions:.0f}, cycles={cycles:.0f}, " f"ipc={metrics['ipc']:.3f}"
                log.debug(msg)
        except (KeyError, TypeError) as e:
            log.warning(f"Could not calculate Perf summary metrics: {e}")
    else:
        log.debug("Perf DataFrame is empty, skipping Perf metrics")

    return metrics


def _load_timeseries_data(snapshot_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """从一个已解包的快照目录中，加载 SAR 和 Perf 的原始时序数据。"""
    level_dir = snapshot_dir / "attach_session"
    df_sar_per_core = pd.DataFrame()
    df_perf_all = pd.DataFrame()

    try:
        sar_csv_path = level_dir / "sar_cpu.csv"
        if sar_csv_path.exists() and sar_csv_path.stat().st_size > 0:
            with open(sar_csv_path, "r") as f:
                lines = f.readlines()

            header_line_content = None
            data_start_idx = 0

            for i, line in enumerate(lines):
                stripped_line = line.strip()
                if stripped_line.startswith("#"):
                    header_line_content = stripped_line[1:].strip()
                    data_start_idx = i + 1
                    break

            if header_line_content:
                from io import StringIO

                data_lines = [line for line in lines[data_start_idx:] if line.strip()]
                csv_content = header_line_content + "\n" + "".join(data_lines)

                df_sar = pd.read_csv(StringIO(csv_content), sep=";")
                if "CPU" in df_sar.columns and not df_sar.empty:
                    df_sar_per_core = df_sar[pd.to_numeric(df_sar["CPU"], errors="coerce").notna()].copy()
            else:
                log.warning(f"Could not find a header line (starting with '#') in {sar_csv_path}")

        perf_txt_path = level_dir / "perf_stat.txt"
        if perf_txt_path.exists():
            perf_content = perf_txt_path.read_text()
            if perf_content:
                df_perf_raw = parse_perf_stat_timeseries(perf_content)
                df_perf_all = df_perf_raw[df_perf_raw["cpu"] == "all"].copy()

    except Exception as e:
        log.error(f"Error loading time-series data from {snapshot_dir}: {e}", exc_info=True)

    return df_sar_per_core, df_perf_all


def run_comparison(input_a: Path, input_b: Path, output_html_path: Optional[Path] = None):
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
            plots = {}
            if not df_sar_a.empty and not df_sar_b.empty:
                df_sar_a["snapshot"] = "A (Baseline)"
                df_sar_b["snapshot"] = "B (Target)"
                df_sar_combined = pd.concat([df_sar_a, df_sar_b], ignore_index=True)
                df_sar_combined["time_elapsed"] = df_sar_combined.groupby("snapshot").cumcount()
                df_sar_combined["%total_cpu"] = df_sar_combined["%user"] + df_sar_combined["%system"]

                fig = px.line(
                    df_sar_combined.groupby(["snapshot", "time_elapsed"]).mean(numeric_only=True).reset_index(),
                    x="time_elapsed",
                    y="%total_cpu",
                    color="snapshot",
                    title="Average CPU Utilization (User + System) Comparison",
                    labels={"time_elapsed": "Time Elapsed (seconds)", "%total_cpu": "Avg CPU Utilization (%)"},
                )
                plots["sar_cpu_overlay"] = fig.to_html(full_html=False, include_plotlyjs="cdn")

            summary_a_html = tabulate(
                [
                    [d["name"], d["format"].format(metrics_a[k])]
                    for k, d in metric_definitions.items()
                    if metrics_a.get(k) is not None
                ],
                headers=["Metric", "Value"],
                tablefmt="html",
            )
            summary_b_html = tabulate(
                [
                    [d["name"], d["format"].format(metrics_b[k])]
                    for k, d in metric_definitions.items()
                    if metrics_b.get(k) is not None
                ],
                headers=["Metric", "Value"],
                tablefmt="html",
            )

            templates_dir = get_project_root() / "src/templates"
            env = Environment(loader=FileSystemLoader(str(templates_dir)))
            template = env.get_template("report_template_compare.html")
            html_content = template.render(
                input_a_name=input_a.name,
                input_b_name=input_b.name,
                summary_table_a=summary_a_html,
                summary_table_b=summary_b_html,
                plots=plots,
            )
            with open(output_html_path, "w") as f:
                f.write(html_content)
            log.info(f"✅ HTML comparison report saved to: {output_html_path}")

        return terminal_report
