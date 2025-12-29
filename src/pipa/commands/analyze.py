"""Archive analysis and HTML report generation."""

from __future__ import annotations

import logging
import pprint
import shutil
import tempfile
from importlib import resources
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import yaml
from markdown_it import MarkdownIt

from pipa.commands.rules import format_rules_to_html_tree, load_rules
from pipa.parser import PARSER_REGISTRY
from pipa.report.context_builder import _parse_cpu_list_str, build_full_context
from pipa.report.hotspots import extract_hotspots
from pipa.report.html_generator import generate_html_report
from pipa.report.plotter import (
    plot_cpu_clusters,
    plot_disk_sunburst,
    plot_per_disk_pies,
    plot_sar_cpu,
    plot_timeseries_generic,
)
from pipa.utils import get_project_root

log = logging.getLogger(__name__)


def _fig_to_html(figure) -> str:
    return figure.to_html(full_html=False, include_plotlyjs=False)


def _generate_disk_analysis_html(warnings: list[str]) -> str:
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
        warning_items = "".join(
            [f"<li style='color: #d9534f;'>{warn}</li>" for warn in warnings]
        )
        warning_html = f"""
        <div class="disk-warnings" style="margin-bottom: 20px; padding: 15px; background: #fff3cd;
             border-radius: 8px; border-left: 4px solid #ffc107;">
            <h4 style="margin-top:0; color: #856404;">⚠️ Capacity Warnings</h4>
            <ul style="margin-bottom: 0; padding-left: 20px;">{warning_items}</ul>
        </div>
        """

    return legend_html + warning_html


def _generate_report(
    level_dir: Path,
    report_path: Path,
    expected_cpus: Optional[str] = None,
    symfs: Optional[str] = None,
    kallsyms: Optional[str] = None,
):
    log.info("Generating analysis report from directory: %s", level_dir)
    analysis_warnings: list[str] = []
    all_dataframes: Dict[str, pd.DataFrame | Dict[str, pd.DataFrame]] = {}

    static_info_str = ""
    static_info_data: Dict[str, Dict] = {}
    try:
        static_info_path = level_dir.parent / "static_info.yaml"
        with open(static_info_path, "r", encoding="utf-8") as file_handle:
            static_info_data = yaml.safe_load(file_handle)
            static_info_str = yaml.dump(static_info_data, indent=2, allow_unicode=True)
        log.info("Loaded static system info from %s", static_info_path.name)
    except FileNotFoundError:
        analysis_warnings.append(
            "static_info.yaml not found. The report will lack system context."
        )

    log.info("Loading data files using parser registry...")
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

    for filename, registry_key in files_to_parse.items():
        file_path = level_dir / filename
        parser_func = PARSER_REGISTRY.get(registry_key)
        if not file_path.exists():
            if filename == "perf_stat.txt":
                analysis_warnings.append(
                    f"{filename} not found. Perf-related analysis will be skipped."
                )
            continue
        if file_path.stat().st_size == 0:
            analysis_warnings.append(f"{filename} is empty.")
            continue
        if not parser_func:
            log.warning("No parser registered for '%s'", registry_key)
            continue
        try:
            if filename.endswith(".txt"):
                df = parser_func(file_path.read_text())
            else:
                df = parser_func(file_path)
            if registry_key == "perf_stat":
                all_dataframes["perf_raw"] = df
            else:
                all_dataframes[registry_key] = df
            log.info("Parsed %s via %s", filename, parser_func.__module__)
        except Exception as exc:  # pragma: no cover - defensive
            log.warning("Failed to process %s: %s", filename, exc, exc_info=True)
            analysis_warnings.append(f"Error parsing {filename}: {exc}")

    if not (level_dir / "perf.data").exists():
        analysis_warnings.append(
            "perf.data not found. Flame graph generation will not be possible."
        )

    project_root = get_project_root()
    rules_path = project_root / "config" / "rules" / "decision_tree.yaml"
    if rules_path.exists():
        rules, rule_configs = load_rules(rules_path)
    else:
        try:
            resource = resources.files("pipa").joinpath(
                "data", "rules", "decision_tree.yaml"
            )
        except Exception:  # pragma: no cover - defensive fallback
            rules, rule_configs = load_rules(rules_path)
        else:
            with resources.as_file(resource) as resolved_path:
                rules, rule_configs = load_rules(Path(resolved_path))
    if expected_cpus:
        rule_configs.setdefault("expected_cpus_str", expected_cpus)

    context = build_full_context(all_dataframes, static_info_data, rule_configs)
    context.update(rule_configs)

    plots: Dict[str, str] = {}
    tables: Dict[str, str] = {}

    if "cpu_features_df" in context:
        df_features = context["cpu_features_df"]
        fig_global = plot_cpu_clusters(
            df_features, title="全景视图：所有 CPU 核心负载分布"
        )
        plots["cpu_cluster_global"] = _fig_to_html(fig_global)
        if expected_cpus:
            target_ids = _parse_cpu_list_str(expected_cpus)
            df_target = df_features[df_features.index.isin(target_ids)]
            if not df_target.empty:
                fig_target = plot_cpu_clusters(
                    df_target, title=f"聚焦视图：业务绑定核心 ({expected_cpus})"
                )
                plots["cpu_cluster_target"] = _fig_to_html(fig_target)
        if "cpu_clusters_summary" in context:
            summary_df = pd.DataFrame(context["cpu_clusters_summary"])
            tables["cluster_summary"] = summary_df.to_json(orient="records")

    log.debug("--- Final Context for Decision Engine ---\n%s", pprint.pformat(context))
    md = MarkdownIt("commonmark", {"html": True})
    audit_html, decision_tree_html, findings_for_tree_html = format_rules_to_html_tree(
        rules, all_dataframes, context, md
    )

    if "perf_raw" in all_dataframes and isinstance(all_dataframes["perf_raw"], dict):
        perf_dict = all_dataframes["perf_raw"]
        frames_to_merge = []
        if (df_events := perf_dict.get("events")) is not None and not df_events.empty:
            frames_to_merge.append(df_events.rename(columns={"event_name": "name"}))
        if (
            df_metrics := perf_dict.get("metrics")
        ) is not None and not df_metrics.empty:
            df_m = df_metrics.rename(columns={"metric_name": "name"}).copy()
            df_m["name"] = df_m["name"] + " (%)"
            frames_to_merge.append(df_m)
        if frames_to_merge:
            df_combined = pd.concat(frames_to_merge)
            if "cpu" not in df_combined.columns:
                df_combined["cpu"] = "all"
            df_combined["cpu"] = df_combined["cpu"].replace("", "all").fillna("all")
            df_perf = df_combined.pivot_table(
                index=["timestamp", "cpu"], columns="name", values="value"
            ).reset_index()
            all_dataframes["perf"] = df_perf

    if static_info_data and "disk_info" in static_info_data:
        try:
            fig_sunburst = plot_disk_sunburst(static_info_data["disk_info"])
            if fig_sunburst and fig_sunburst.data:
                plots["disk_sunburst"] = _fig_to_html(fig_sunburst)
            fig_pies = plot_per_disk_pies(static_info_data["disk_info"])
            if fig_pies and fig_pies.data:
                plots["disk_breakdown"] = _fig_to_html(fig_pies)
        except Exception as exc:  # pragma: no cover - visualization best-effort
            log.warning("Failed to generate disk charts: %s", exc)
        warnings_list: list[str] = []
        devices = static_info_data["disk_info"].get("block_devices", [])
        for disk in devices:
            if "fs_usage" in disk:
                pct = disk["fs_usage"]["percent"]
                mount = disk["fs_usage"]["mount"]
                if pct > 90:
                    warnings_list.append(
                        f"Critical: <strong>{disk['name']}</strong> ({mount}) usage is at <strong>{pct}%</strong>"
                    )
                elif pct > 80:
                    warnings_list.append(
                        f"Warning: <strong>{disk['name']}</strong> ({mount}) usage is at <strong>{pct}%</strong>"
                    )
            for part in disk.get("partitions", []):
                if "fs_usage" in part:
                    pct = part["fs_usage"]["percent"]
                    mount = part["fs_usage"]["mount"]
                    if pct > 90:
                        warnings_list.append(
                            f"Critical: Partition <strong>{part['name']}</strong> ({mount}) usage is at <strong>{pct}%</strong>"
                        )
                    elif pct > 80:
                        warnings_list.append(
                            f"Warning: Partition <strong>{part['name']}</strong> ({mount}) usage is at <strong>{pct}%</strong>"
                        )
        context["disk_analysis_html"] = _generate_disk_analysis_html(warnings_list)

    for name, df in all_dataframes.items():
        if name == "perf_raw" or (isinstance(df, pd.DataFrame) and df.empty):
            continue
        log.info("Processing data for '%s'...", name)
        if isinstance(df, pd.DataFrame):
            tables[name] = df.round(2).to_json(orient="records")
        if isinstance(df, pd.DataFrame) and "timestamp" in df.columns:
            try:
                if name == "sar_cpu":
                    figure, filters = plot_sar_cpu(df, context)
                    plots[name] = _fig_to_html(figure)
                    context[f"{name}_filters"] = filters
                else:
                    generated_plots, generated_filters = plot_timeseries_generic(
                        df, name
                    )
                    for plot_name, figure in generated_plots.items():
                        plots[plot_name] = _fig_to_html(figure)
                    context.update(generated_filters)
            except Exception as exc:  # pragma: no cover - visualization best-effort
                log.warning(
                    "Could not generate plot for '%s': %s", name, exc, exc_info=True
                )

    perf_data_path = level_dir / "perf.data"
    if perf_data_path.exists():
        log.info("Extracting hotspots from perf.data...")
        hotspots_data = extract_hotspots(
            perf_data_path, symfs_dir=symfs, kallsyms_path=kallsyms
        )
        if hotspots_data:
            import json

            tables["hotspots"] = json.dumps(hotspots_data)
            log.info("Extracted %s hotspots.", len(hotspots_data))
        else:
            log.info("No hotspots extracted (perf report returned empty or failed).")

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
            key: value.tolist() if hasattr(value, "tolist") else value
            for key, value in context.items()
            if not isinstance(value, pd.DataFrame)
        },
        audit_html=audit_html,
    )


def _get_unique_output_path(base_path: Path) -> Path:
    if not base_path.exists():
        return base_path
    stem = base_path.stem
    suffix = base_path.suffix
    parent = base_path.parent
    counter = 1
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        candidate = parent / new_name
        if not candidate.exists():
            return candidate
        counter += 1


def analyze_archive(
    input_path: str,
    output_path: Optional[str] = None,
    expected_cpus: Optional[str] = None,
    symfs: Optional[str] = None,
    kallsyms: Optional[str] = None,
) -> Path:
    """Analyze a pipa-tree archive and write an HTML report."""

    input_path_obj = Path(input_path)
    if output_path is None:
        output_path_obj = _get_unique_output_path(Path("report.html").resolve())
    else:
        output_path_obj = Path(output_path)

    with tempfile.TemporaryDirectory(prefix="pipa_analyze_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        log.info("Unpacking archive '%s' for analysis...", input_path_obj)
        shutil.unpack_archive(input_path_obj, temp_dir, format="gztar")

        level_dir: Optional[Path] = None
        unpacked_items = list(temp_dir.iterdir())
        if len(unpacked_items) == 1 and unpacked_items[0].is_dir():
            level_dir = unpacked_items[0]
        else:
            for item in unpacked_items:
                if item.is_dir() and item.name.startswith("attach_session"):
                    level_dir = item
                    break

        if not level_dir:
            raise FileNotFoundError("No valid data directory found in the archive.")

        _generate_report(
            level_dir,
            output_path_obj,
            expected_cpus=expected_cpus,
            symfs=symfs,
            kallsyms=kallsyms,
        )

    log.info("Analysis complete. Report saved to %s", output_path_obj)
    return output_path_obj
