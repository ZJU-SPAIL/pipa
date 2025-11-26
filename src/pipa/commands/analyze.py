"""
分析命令模块

此模块实现analyze命令，用于分析采样数据并生成综合HTML报告。
解析各种性能数据文件，应用规则引擎，生成可视化和决策树分析。
"""

import logging
import pprint
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import click
import pandas as pd
import yaml
from markdown_it import MarkdownIt

from src.pipa.parsers import PARSER_REGISTRY
from src.pipa.report.context_builder import build_full_context
from src.pipa.report.html_generator import generate_html_report
from src.pipa.report.plotter import (
    plot_cpu_clusters,
    plot_disk_sunburst,
    plot_per_disk_pies,
    plot_sar_cpu,
    plot_timeseries_generic,
)
from src.utils import get_project_root

from .rules import format_rules_to_html_tree, load_rules

log = logging.getLogger(__name__)


def _generate_disk_analysis_html(warnings: list) -> str:
    """生成磁盘分析的 HTML 摘要 (图例 + 警告)。"""
    legend_html = """
    <div class="disk-legend" style="margin-bottom: 20px; padding: 15px; background: #f8f9fa;
         border-radius: 8px; border-left: 4px solid #1f77b4;">
        <h4 style="margin-top:0;">📊 Storage Color Guide</h4>
        <ul style="list-style: none; padding: 0; display: flex; gap: 20px; margin-bottom: 10px;">
            <li><span style="display:inline-block;width:12px;height:12px;background:#2ca02c;
                 border-radius:50%;margin-right:5px;"></span><strong>SSD / NVMe</strong> (High Performance)</li>
            <li><span style="display:inline-block;width:12px;height:12px;background:#1f77b4;
                 border-radius:50%;margin-right:5px;"></span><strong>HDD / SATA</strong> (Standard Storage)</li>
            <li><span style="display:inline-block;width:12px;height:12px;background:#9467bd;
                 border-radius:50%;margin-right:5px;"></span><strong>LVM / Logical</strong> (Virtual Volume)</li>
        </ul>
        <p style="font-size: 0.9em; color: #666; margin: 0;">
            * Red text in charts indicates filesystem usage > 90%. Click on any disk slice to zoom in for details.
        </p>
    </div>
    """

    warning_html = ""
    if warnings:
        warning_items = "".join([f"<li style='color: #d9534f;'>{w}</li>" for w in warnings])
        warning_html = f"""
        <div class="disk-warnings" style="margin-bottom: 20px; padding: 15px; background: #fff3cd;
             border-radius: 8px; border-left: 4px solid #ffc107;">
            <h4 style="margin-top:0; color: #856404;">⚠️ Capacity Warnings</h4>
            <ul style="margin-bottom: 0; padding-left: 20px;">{warning_items}</ul>
        </div>
        """

    return legend_html + warning_html


def _generate_report(level_dir: Path, report_path: Path, expected_cpus: Optional[str] = None):
    """
    分析所有可用的采样数据并生成综合HTML报告。
    分析所有可用的采样数据并生成综合HTML报告。

    这是核心引擎逻辑，从采样目录加载数据，解析文件，
    应用规则引擎，生成图表和决策树分析。

    参数:
        level_dir: 包含采样数据的目录路径。
        report_path: 输出HTML报告的文件路径。
    """
    log.info(f"--- Generating analysis report from directory: {level_dir} ---")
    analysis_warnings = []  # 收集分析过程中的警告信息
    all_dataframes = {}  # 存储所有解析后的数据框

    # 加载静态系统信息，用于上下文构建
    static_info_str, static_info_data = "", {}
    try:
        static_info_path = level_dir.parent / "static_info.yaml"
        with open(static_info_path, "r") as f:
            static_info_data = yaml.safe_load(f)
            static_info_str = yaml.dump(static_info_data, indent=2, allow_unicode=True)
        log.info(f"Loaded static system info from {static_info_path.name}.")
    except FileNotFoundError:
        analysis_warnings.append("static_info.yaml not found. The report will lack system context.")

    log.info("Dynamically loading all data files using the parser registry...")

    # 定义需要解析的文件映射：文件名 -> 解析器键
    files_to_parse = {
        "perf_stat.txt": "perf_stat",
        "sar_cpu.csv": "sar_cpu",
        "sar_network.csv": "sar_network",
        "sar_io.csv": "sar_io",
        "sar_disk.csv": "sar_disk",
        "sar_memory.csv": "sar_memory",
        "sar_paging.csv": "sar_paging",
        "sar_load.csv": "sar_load",
    }

    # 遍历所有文件，使用注册的解析器进行解析
    for filename, registry_key in files_to_parse.items():
        file_path = level_dir / filename
        parser_func = PARSER_REGISTRY.get(registry_key)

        # 检查文件是否存在和非空
        if not file_path.exists():
            if filename == "perf_stat.txt":
                analysis_warnings.append(f"{filename} not found. Perf-related analysis will be skipped.")
            continue
        if file_path.stat().st_size == 0:
            analysis_warnings.append(f"{filename} is empty.")
            continue

        # 使用相应的解析器解析文件
        if parser_func:
            try:
                # 根据文件类型选择解析方式
                if filename.endswith(".txt"):
                    content = file_path.read_text()
                    df = parser_func(content)
                else:
                    df = parser_func(file_path)

                # 特殊处理perf数据
                if registry_key == "perf_stat":
                    all_dataframes["perf_raw"] = df
                else:
                    all_dataframes[registry_key] = df
                log.info(f"Successfully parsed {filename} using '{parser_func.__module__}'.")

            except Exception as e:
                log.warning(f"Failed to process {filename} with its parser: {e}", exc_info=True)
                analysis_warnings.append(f"Error parsing {filename}: {e}")
        else:
            log.warning(f"No parser registered for '{registry_key}', skipping file.")

    # 检查flame graph数据是否存在
    if not (level_dir / "perf.data").exists():
        analysis_warnings.append("perf.data not found. Flame graph generation will not be possible.")

    # 加载决策树规则配置
    project_root = get_project_root()
    rules_path = project_root / "config/rules/decision_tree.yaml"
    rules, rule_configs = load_rules(rules_path)

    # === 把参数注入到配置里 ===
    if expected_cpus:
        rule_configs["expected_cpus_str"] = expected_cpus

    # 构建完整的分析上下文，包含所有派生指标
    context = build_full_context(all_dataframes, static_info_data, rule_configs)
    context.update(rule_configs)

    plots = {}  # 存储生成的图表HTML
    tables = {}  # 存储数据表的JSON表示

    if "cpu_features_df" in context:

        # 我们从 context 中获取 optimal_eps 只是为了在标题中显示，它不再参与决策
        optimal_eps_for_title = context.get("optimal_eps", 0.0)
        fig_clusters = plot_cpu_clusters(context["cpu_features_df"], optimal_eps_for_title)
        plots["cpu_cluster_analysis"] = fig_clusters.to_html(full_html=False, include_plotlyjs="cdn")

        if "cpu_clusters_summary" in context:
            summary_df = pd.DataFrame(context["cpu_clusters_summary"])
            tables["cluster_summary"] = summary_df.to_json(orient="records")

    log.debug("--- [DEBUG] Final Context for Decision Engine ---")
    log.debug(f"\n{pprint.pformat(context)}")
    log.debug("-------------------------------------------------")

    # 生成决策树HTML和发现结果
    md = MarkdownIt("commonmark", {"html": True})  # 启用HTML支持，允许在Markdown中嵌入HTML标签
    decision_tree_html, findings_for_tree_html = format_rules_to_html_tree(rules, all_dataframes, context, md)

    # 处理perf数据：将原始数据透视为宽格式，便于分析
    # 注意：perf_raw 现在是字典 {'events': df, 'metrics': df}
    if "perf_raw" in all_dataframes and isinstance(all_dataframes["perf_raw"], dict):
        perf_dict = all_dataframes["perf_raw"]
        frames_to_merge = []

        # 1. 获取 Events (原始计数)
        if (df_events := perf_dict.get("events")) is not None and not df_events.empty:
            # 为了统一合并，重命名列
            df_e = df_events.rename(columns={"event_name": "name"})
            frames_to_merge.append(df_e)

        # 2. 获取 Metrics (百分比指标) -> === 核心修复 ===
        if (df_metrics := perf_dict.get("metrics")) is not None and not df_metrics.empty:
            df_m = df_metrics.rename(columns={"metric_name": "name"})

            # 关键技巧：给 Metric 名字加上 (%) 后缀
            # 这样 plotter.py 会自动把它识别为百分比，并生成独立的 "Perf Percentages" 图表
            # 既保留了证据，又不会和几十亿的 cycles 混在一起
            df_m["name"] = df_m["name"] + " (%)"

            frames_to_merge.append(df_m)

        # 3. 合并并透视
        if frames_to_merge:
            df_combined = pd.concat(frames_to_merge)

            # === FIX: 简化逻辑 ===
            # 现在 collector 不再输出 Per-Core 数据，数据天然就是聚合的。
            # Parser 会将 system-wide 的数据标记为 cpu='all' (或空)。
            # 我们只需要确保 cpu 列存在且一致。

            if "cpu" not in df_combined.columns:
                df_combined["cpu"] = "all"

            # 填补可能的空值
            df_combined["cpu"] = df_combined["cpu"].replace("", "all").fillna("all")

            # 直接透视。如果有重复时间戳(极少见)，pivot_table 默认 mean 聚合，也是安全的。
            df_perf = df_combined.pivot_table(index=["timestamp", "cpu"], columns="name", values="value").reset_index()

            all_dataframes["perf"] = df_perf

    # 7. 磁盘分析 (可视化 + 诊断摘要)
    if static_info_data and "disk_info" in static_info_data:
        # 7a. 生成图表
        try:
            log.info("Generating Disk Visualization Charts...")
            fig_sunburst = plot_disk_sunburst(static_info_data["disk_info"])
            if fig_sunburst and fig_sunburst.data:
                plots["disk_sunburst"] = fig_sunburst.to_html(full_html=False, include_plotlyjs="cdn")

            fig_pies = plot_per_disk_pies(static_info_data["disk_info"])
            if fig_pies and fig_pies.data:
                plots["disk_breakdown"] = fig_pies.to_html(full_html=False, include_plotlyjs="cdn")
        except Exception as e:
            log.warning(f"Failed to generate disk charts: {e}")

        # 7b. 生成诊断摘要 (Legend + Warnings)
        warnings = []
        devices = static_info_data["disk_info"].get("block_devices", [])
        for disk in devices:
            # 检查磁盘本身
            if "fs_usage" in disk:
                pct = disk["fs_usage"]["percent"]
                mount = disk["fs_usage"]["mount"]
                if pct > 90:
                    warnings.append(
                        f"Critical: <strong>{disk['name']}</strong> ({mount}) usage is at <strong>{pct}%</strong>"
                    )
                elif pct > 80:
                    warnings.append(
                        f"Warning: <strong>{disk['name']}</strong> ({mount}) usage is at <strong>{pct}%</strong>"
                    )

            # 检查分区
            for part in disk.get("partitions", []):
                if "fs_usage" in part:
                    pct = part["fs_usage"]["percent"]
                    mount = part["fs_usage"]["mount"]
                    if pct > 90:
                        warnings.append(
                            f"Critical: Partition <strong>{part['name']}</strong> ({mount}) "
                            f"usage is at <strong>{pct}%</strong>"
                        )
                    elif pct > 80:
                        warnings.append(
                            f"Warning: Partition <strong>{part['name']}</strong> ({mount}) "
                            f"usage is at <strong>{pct}%</strong>"
                        )

        context["disk_analysis_html"] = _generate_disk_analysis_html(warnings)

    # 8. 生成时序图表
    for name, df in all_dataframes.items():
        if name == "perf_raw" or (isinstance(df, pd.DataFrame) and df.empty):
            continue

        log.info(f"Processing data for '{name}'...")
        # 将数据框转换为JSON格式，用于前端显示
        tables[name] = df.round(2).to_json(orient="records")

        try:
            if "timestamp" not in df.columns:
                continue

            # 特殊处理CPU数据：生成专用图表和过滤器
            if name == "sar_cpu":
                fig = plot_sar_cpu(df)
                plots[name] = fig.to_html(full_html=False, include_plotlyjs="cdn")

                # 构建前端过滤器选项
                metrics_to_plot = [m for m in ["%user", "%system", "%iowait", "%idle", "%total"] if m in df.columns]
                filter_options = {"CPU": sorted(df["CPU"].unique().tolist()), "METRIC": metrics_to_plot}
                filters_with_hints = {}
                for key, values in filter_options.items():
                    filters_with_hints[key] = {
                        "values": values,
                        "sample": values[:3],
                        "count": len(values),
                        "source": "legendgroup" if key == "CPU" else "name",
                    }
                context[f"{name}_filters"] = filters_with_hints
            else:
                # 为其他时间序列数据生成通用图表
                generated_plots, generated_filters = plot_timeseries_generic(df, name)
                for plot_name, fig in generated_plots.items():
                    plots[plot_name] = fig.to_html(full_html=False, include_plotlyjs="cdn")
                context.update(generated_filters)
        except Exception as e:
            log.warning(f"Could not generate plot for '{name}': {e}", exc_info=True)

    # 9. 生成最终报告
    generate_html_report(
        output_path=report_path,
        md_instance=md,
        warnings=analysis_warnings,
        plots=plots,
        tables_json=tables,
        decision_tree_html=decision_tree_html,
        findings_for_tree_html=findings_for_tree_html,
        static_info_data=static_info_data,
        static_info_str=static_info_str,
        context={
            k: v.tolist() if hasattr(v, "tolist") else v for k, v in context.items() if not isinstance(v, pd.DataFrame)
        },
    )


def _get_unique_output_path(base_path: Path) -> Path:
    """
    通过追加数字生成唯一的输出文件路径，如果文件已存在。

    参数:
        base_path: 基础文件路径。

    返回:
        唯一的文件路径。
    """
    if not base_path.exists():
        return base_path
    stem = base_path.stem
    suffix = base_path.suffix
    parent = base_path.parent
    counter = 1
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
        counter += 1


@click.command()
@click.option(
    "--input",
    "input_path_str",
    required=True,
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to the .pipa archive to analyze.",
)
@click.option(
    "--output",
    "output_path_str",
    required=False,
    type=click.Path(writable=True, dir_okay=False, resolve_path=True),
    default=None,
    help="Path to save the generated HTML report. If not specified, generates 'report.html' in current directory.",
)
@click.option(
    "--expected-cpus",
    default=None,
    help="Validation: Comma-separated list of CPUs expected to be busy (e.g. '0-7,16').",
)
def analyze(input_path_str: str, output_path_str: str, expected_cpus: str):
    """
    分析采样结果并生成综合HTML报告。

    解压.pipa归档文件，解析其中的性能数据，
    应用分析规则，生成包含图表和决策树的HTML报告。
    """
    input_path = Path(input_path_str)

    if output_path_str is None:
        output_path = _get_unique_output_path(Path("report.html").resolve())
    else:
        output_path = Path(output_path_str)
        # 如果明确指定了输出路径，直接使用（允许覆盖），只有默认路径时才自动编号

    with tempfile.TemporaryDirectory(prefix="pipa_analyze_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        click.echo(f"Unpacking archive '{input_path.name}' for analysis...")
        shutil.unpack_archive(input_path, temp_dir, format="gztar")

        level_dir = None
        unpacked_items = list(temp_dir.iterdir())
        if len(unpacked_items) == 1 and unpacked_items[0].is_dir():
            level_dir = unpacked_items[0]
        else:
            for item in unpacked_items:
                if item.is_dir() and item.name.startswith("attach_session"):
                    level_dir = item
                    break

        if not level_dir:
            click.secho("Error: No valid data directory found in the archive.", fg="red")
            raise click.Abort()

        try:
            _generate_report(level_dir, output_path, expected_cpus=expected_cpus)
            click.secho(f"\n✅ Analysis complete. Report saved to: {output_path}", fg="green")
        except Exception as e:
            click.secho(f"❌ An error occurred during report generation: {e}", fg="red")
            raise click.Abort()
