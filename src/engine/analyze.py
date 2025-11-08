import logging
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
from jinja2 import Environment, FileSystemLoader
from markdown_it import MarkdownIt

from src.engine.rules import calculate_context_metrics, format_rules_to_html_tree, load_rules, run_rules_engine
from src.parsers.perf_stat_timeseries_parser import parse_perf_stat_timeseries
from src.parsers.sar_timeseries_parser import parse_sar_timeseries

log = logging.getLogger(__name__)


def generate_report(level_dir: Path, report_path: Path):
    """
    Analyzes sampling data, generates insights and interactive plots,
    and creates a self-contained HTML report.
    """
    log.info(f"--- Generating analysis report from directory: {level_dir} ---")

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

    if report_path:
        all_dataframes = {"perf": df_perf, **results_sar}
        rules = load_rules(Path("config/rules/decision_tree.yaml"))

        context = calculate_context_metrics(all_dataframes)

        findings = run_rules_engine(all_dataframes, rules, context)
        log.info(f"规则引擎找到了 {len(findings)} 条洞察。")
        md = MarkdownIt()
        decision_tree_html, findings_for_tree_html = format_rules_to_html_tree(rules, all_dataframes, context, md)
        log.info("Generating interactive plot...")
        columns_to_plot = [
            col for col in merged_df.columns if pd.api.types.is_numeric_dtype(merged_df[col]) and "timestamp" not in col
        ]

        fig = px.line(
            merged_df,
            x="timestamp_x",
            y=columns_to_plot,
            title="Time-Series Metrics Explorer",
            labels={"timestamp_x": "Time", "value": "Metric Value", "variable": "Metric"},
        )
        fig.update_layout(autosize=True, height=600, legend_itemclick="toggleothers")
        plot_div = fig.to_html(full_html=False, include_plotlyjs="cdn")
        df_for_table = merged_df.round(2).replace([np.inf, -np.inf], "Infinity").fillna("N/A")
        table_json_data = df_for_table.to_json(orient="records")
        log.info(f"Generating HTML report at: {report_path}")
        env = Environment(loader=FileSystemLoader("src/templates"))

        md = MarkdownIt()
        env.filters["markdown"] = lambda text: md.render(text)

        template = env.get_template("report_template.html")
        html_content = template.render(
            interactive_plot=plot_div,
            table_data_json=table_json_data,
            findings=findings,
            decision_tree_html=decision_tree_html,
            findings_for_tree_html=findings_for_tree_html,
        )
        with open(report_path, "w") as f:
            f.write(html_content)
        log.info("✅ HTML report with insights generated successfully.")

    return merged_df
