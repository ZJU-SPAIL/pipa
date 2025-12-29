"""Context construction utilities for report generation."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Set, cast

import pandas as pd

from pipa.report.cluster_analyzer import analyze_cpu_clusters
from pipa.utils import p95

log = logging.getLogger(__name__)


def _parse_cpu_list_str(cpu_list_str: str) -> Set[str]:
    """Parse Linux-style CPU list strings (e.g., ``"0-3,8"``) into a set of IDs."""

    cpus: Set[str] = set()
    if not cpu_list_str:
        return cpus

    cpu_list_str = cpu_list_str.strip()
    parts = cpu_list_str.split(",")
    for part in parts:
        part = part.strip()
        if "-" in part:
            try:
                start, end = map(int, part.split("-"))
            except ValueError:
                continue
            for cpu_id in range(start, end + 1):
                cpus.add(str(cpu_id))
        elif part.isdigit():
            cpus.add(part)
    return cpus


def _format_cpu_list_to_range(cpu_list: list[Any]) -> str:
    """Convert ``[0, 1, 2, 4]`` into a compact ``"0-2,4"`` string."""

    if not cpu_list:
        return "None"
    try:
        sorted_cpus = sorted(int(cpu) for cpu in cpu_list)
    except ValueError:
        return ",".join(map(str, cpu_list))

    if not sorted_cpus:
        return "None"

    ranges = []
    range_start = sorted_cpus[0]
    for index in range(1, len(sorted_cpus)):
        if sorted_cpus[index] > sorted_cpus[index - 1] + 1:
            if range_start == sorted_cpus[index - 1]:
                ranges.append(str(range_start))
            else:
                ranges.append(f"{range_start}-{sorted_cpus[index - 1]}")
            range_start = sorted_cpus[index]
    if range_start == sorted_cpus[-1]:
        ranges.append(str(range_start))
    else:
        ranges.append(f"{range_start}-{sorted_cpus[-1]}")
    return ",".join(ranges)


def build_full_context(
    df_dict: Dict[str, pd.DataFrame],
    static_info: Dict[str, Any],
    rule_configs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the derived metric context used by rules, plots, and templates."""

    context: Dict[str, Any] = {
        "num_cpu": 1,
        "total_cpu": 0.0,
        "avg_cswch": 0.0,
        "total_tps": 0.0,
        "avg_swaps": 0.0,
        "avg_load1": 0.0,
        "ipc": 0.0,
        "branch_miss_rate": 0.0,
        "l3_cache_miss_rate": 0.0,
        "avg_iowait": 0.0,
        "avg_nvcswch_s": 0.0,
        "cpu_util_std_dev": 0.0,
        "cpu_max_util": 0.0,
        "cpu_min_util": 0.0,
        "cpu_clusters_count": 0,
        "cpu_clusters_summary": [],
        "is_numa_imbalanced": False,
        "numa_nodes_count": 1,
        "numa_max_diff": 0.0,
        "numa_status_msg": "Non-NUMA or Single Node",
        "iowait_core_count": 0,
        "is_cpu_imbalanced": False,
        "avg_disk_util": 0.0,
        "max_disk_util": 0.0,
        "p95_disk_util": 0.0,
        "avg_disk_await": 0.0,
        "max_disk_await": 0.0,
        "p95_disk_await": 0.0,
        "p95_avgqu_sz": 0.0,
        "busiest_disk_name": "None",
        "busiest_disk_type": "Unknown",
        "busiest_disk_subtype": "Unknown",
        "avg_ifutil": 0.0,
        "effective_await_threshold": 0.0,
    }

    if static_info and (cpu_info := static_info.get("cpu_info")):
        context["num_cpu"] = cpu_info.get("CPU(s)", 1)

    expected_str = rule_configs.get("expected_cpus_str") if rule_configs else None

    df_cpu = df_dict.get("sar_cpu")
    df_per_core = pd.DataFrame()
    if df_cpu is not None and not df_cpu.empty:
        df_per_core = cast(pd.DataFrame, df_cpu[df_cpu["CPU"] != "all"].copy())
        target_cpus = None

        if not df_per_core.empty:
            if "%user" in df_per_core.columns and "%system" in df_per_core.columns:
                df_per_core["%total"] = df_per_core["%user"] + df_per_core["%system"]
            else:
                df_per_core["%total"] = 0.0

            clustering_results = analyze_cpu_clusters(df_per_core, config=rule_configs)
            if clustering_results:
                context.update(clustering_results)
                clusters_summary = context.get("cpu_clusters_summary", [])
                is_imbalanced = False
                if len(clusters_summary) > 1:
                    has_busy = any(
                        cluster.get("id") == 1 for cluster in clusters_summary
                    )
                    if has_busy:
                        is_imbalanced = True
                context["is_cpu_imbalanced"] = is_imbalanced

            core_utils = df_per_core.groupby("CPU").agg(
                {"%total": "mean", "%iowait": ["mean", p95, "max"]}
            )
            context["cpu_util_std_dev"] = core_utils[("%total", "mean")].std()
            context["cpu_max_util"] = core_utils[("%total", "mean")].max()
            context["cpu_min_util"] = core_utils[("%total", "mean")].min()

            if ("%iowait", "p95") in core_utils.columns:
                context["p95_single_core_iowait"] = core_utils[("%iowait", "p95")].max()
                context["max_single_core_iowait"] = core_utils[("%iowait", "max")].max()
                io_wait_threshold = (
                    rule_configs.get("IO_WAIT_HIGH_THRESHOLD", 10.0)
                    if rule_configs
                    else 10.0
                )
                high_iowait_series = core_utils[("%iowait", "p95")]
                bad_cores = high_iowait_series[high_iowait_series > io_wait_threshold]
                context["iowait_core_count"] = len(bad_cores)
                if not bad_cores.empty:
                    sorted_bad_cpus = sorted(int(cpu) for cpu in bad_cores.index)
                    affected_range = _format_cpu_list_to_range(sorted_bad_cpus)
                    longest_seq: list[int] = []
                    current_seq: list[int] = []
                    if sorted_bad_cpus:
                        current_seq = [sorted_bad_cpus[0]]
                        for idx in range(1, len(sorted_bad_cpus)):
                            if sorted_bad_cpus[idx] == sorted_bad_cpus[idx - 1] + 1:
                                current_seq.append(sorted_bad_cpus[idx])
                            else:
                                if len(current_seq) > len(longest_seq):
                                    longest_seq = current_seq
                                current_seq = [sorted_bad_cpus[idx]]
                        if len(current_seq) > len(longest_seq):
                            longest_seq = current_seq
                    zone_desc = ""
                    if len(longest_seq) > 4:
                        seq_indices = [
                            str(cpu)
                            for cpu in longest_seq
                            if str(cpu) in bad_cores.index
                        ]
                        if seq_indices:
                            zone_avg = bad_cores.loc[seq_indices].mean()
                            zone_desc = f"; 重灾区: {longest_seq[0]}-{longest_seq[-1]} (均值 {zone_avg:.1f}%)"
                    top_bad = bad_cores.sort_values(ascending=False).head(3)
                    top_details = [
                        f"CPU {cpu}={val:.1f}%" for cpu, val in top_bad.items()
                    ]
                    top_str = ", ".join(top_details)
                    context["iowait_core_details"] = (
                        f"范围: {affected_range}{zone_desc}; Top3: {top_str}"
                    )
                else:
                    context["iowait_core_details"] = "无"

            if target_cpus:
                context["total_cpu"] = df_per_core["%total"].mean()
                if "%iowait" in df_per_core.columns:
                    context["avg_iowait"] = df_per_core["%iowait"].mean()
            else:
                df_cpu_all = df_cpu[df_cpu["CPU"] == "all"]
                if not df_cpu_all.empty:
                    context["total_cpu"] = (
                        df_cpu_all.get("%user", pd.Series(0)).mean()
                        + df_cpu_all.get("%system", pd.Series(0)).mean()
                    )
                    context["avg_iowait"] = df_cpu_all.get(
                        "%iowait", pd.Series(0)
                    ).mean()
                    context["avg_irq_percent"] = df_cpu_all.get(
                        "%irq", pd.Series(0)
                    ).mean()
                    context["avg_softirq_percent"] = df_cpu_all.get(
                        "%soft", pd.Series(0)
                    ).mean()

            numa_info = static_info.get("numa_info", {}) if static_info else {}
            numa_topology = numa_info.get("numa_topology", {})
            if numa_topology and len(numa_topology) > 1:
                context["numa_cpu_map"] = {
                    node_name.replace("node", "numa_node_"): cpu_list_str
                    for node_name, cpu_list_str in numa_topology.items()
                }
                context["numa_nodes_count"] = len(numa_topology)
                cpu_to_node: Dict[str, str] = {}
                for node_name, cpu_list_str in numa_topology.items():
                    cpu_set = _parse_cpu_list_str(str(cpu_list_str))
                    for cpu_id in cpu_set:
                        cpu_to_node[cpu_id] = node_name
                df_per_core["NUMA_Node"] = df_per_core["CPU"].map(cpu_to_node)
                node_stats = df_per_core.groupby("NUMA_Node")["%total"].mean()
                if not node_stats.empty:
                    min_node_util = node_stats.min()
                    max_node_util = node_stats.max()
                    context["numa_max_diff"] = max_node_util - min_node_util
                    status_parts = [
                        f"{node}: <strong>{util:.1f}%</strong>"
                        for node, util in node_stats.items()
                    ]
                    context["numa_status_msg"] = ", ".join(status_parts)

        if expected_str and not df_per_core.empty:
            workload_avg_df = (
                df_per_core.groupby("timestamp").mean(numeric_only=True).reset_index()
            )
            workload_avg_df["CPU"] = "workload_avg"
            first_row = df_cpu.iloc[0]
            workload_avg_df["hostname"] = first_row.get("hostname", "unknown")
            workload_avg_df["interval"] = first_row.get("interval", 1)
            cols_order = df_cpu.columns.tolist()
            workload_avg_df = workload_avg_df[
                [col for col in cols_order if col in workload_avg_df.columns]
            ]
            df_dict["sar_cpu"] = pd.concat([df_cpu, workload_avg_df], ignore_index=True)
            log.info(
                "Injected 'workload_avg' series into sar_cpu data for business-centric view."
            )

    df_io = df_dict.get("sar_io")
    if df_io is not None and not df_io.empty:
        context["total_tps"] = df_io.get("tps", pd.Series(0)).sum()
        context["avg_await"] = df_io.get("await", pd.Series(0)).mean()
        context["avg_util"] = df_io.get("%util", pd.Series(0)).mean()
        context["avg_avgrq_sz"] = df_io.get("avgrq-sz", pd.Series(0)).mean()
        context["avg_avgqu_sz"] = df_io.get("avgqu-sz", pd.Series(0)).mean()

    df_disk = df_dict.get("sar_disk")
    context.update(
        {
            "max_disk_util": 0.0,
            "max_disk_await": 0.0,
            "busiest_disk_name": "None",
            "avg_avgrq_sz_kb": 0.0,
            "avg_avgqu_sz": 0.0,
            "disk_throughput_mb": 0.0,
            "busiest_disk_subtype": "Unknown",
        }
    )

    if df_disk is not None and not df_disk.empty:
        valid_disks = df_disk[~df_disk["DEV"].str.contains("loop|ram|zram")]
        if not valid_disks.empty:
            numeric_cols = valid_disks.select_dtypes(include=["number"]).columns
            disk_stats = valid_disks.groupby("DEV")[numeric_cols].agg(
                ["mean", "max", p95]
            )
            busiest_dev = ""
            if not disk_stats.empty:
                busiest_dev = disk_stats[("%util", "mean")].idxmax()
                stats = disk_stats.loc[busiest_dev]
                context["busiest_disk_name"] = busiest_dev
                context["avg_disk_util"] = stats.get(("%util", "mean"), 0.0)
                context["max_disk_util"] = stats.get(("%util", "max"), 0.0)
                context["p95_disk_util"] = stats.get(("%util", "p95"), 0.0)
                context["avg_disk_await"] = stats.get(("await", "mean"), 0.0)
                context["max_disk_await"] = stats.get(("await", "max"), 0.0)
                context["p95_disk_await"] = stats.get(("await", "p95"), 0.0)
                queue_col = (
                    "aqu-sz" if ("aqu-sz", "mean") in stats.index else "avgqu-sz"
                )
                context["avg_avgqu_sz"] = stats.get((queue_col, "mean"), 0.0)
                context["max_avgqu_sz"] = stats.get((queue_col, "max"), 0.0)
                context["p95_avgqu_sz"] = stats.get((queue_col, "p95"), 0.0)
                size_col = (
                    "areq-sz" if ("areq-sz", "mean") in stats.index else "avgrq-sz"
                )
                context["avg_avgrq_sz_kb"] = stats.get((size_col, "mean"), 0.0) / 2.0
                context["disk_rkB_s"] = stats.get(("rkB/s", "mean"), 0.0)
                context["disk_wkB_s"] = stats.get(("wkB/s", "mean"), 0.0)
                context["disk_throughput_mb"] = (
                    context["disk_rkB_s"] + context["disk_wkB_s"]
                ) / 1024.0

            if static_info and "disk_info" in static_info:
                devices = static_info["disk_info"].get("block_devices", [])
                for device in devices:
                    if device.get("name") == busiest_dev or any(
                        partition.get("name") == busiest_dev
                        for partition in device.get("partitions", [])
                    ):
                        context["busiest_disk_type"] = device.get(
                            "rotational", "Unknown"
                        )
                        break

            disk_type = context.get("busiest_disk_type", "Unknown")
            disk_name = str(context.get("busiest_disk_name", ""))
            if disk_type == "HDD":
                context["busiest_disk_subtype"] = "HDD"
            elif disk_type == "SSD":
                context["busiest_disk_subtype"] = (
                    "NVME_SSD" if "nvme" in disk_name else "SATA_SSD"
                )

            subtype = context.get("busiest_disk_subtype")
            effective_threshold = 0.0
            if subtype == "SATA_SSD":
                effective_threshold = (
                    rule_configs.get("IO_AWAIT_SATA_SSD_THRESHOLD", 0.0)
                    if rule_configs
                    else 5.0
                )
            elif subtype == "NVME_SSD":
                effective_threshold = (
                    rule_configs.get("IO_AWAIT_NVME_SSD_THRESHOLD", 0.0)
                    if rule_configs
                    else 1.0
                )
            elif subtype == "HDD":
                effective_threshold = (
                    rule_configs.get("IO_AWAIT_HDD_THRESHOLD", 0.0)
                    if rule_configs
                    else 30.0
                )
            context["effective_await_threshold"] = effective_threshold

    df_paging = df_dict.get("sar_paging")
    if df_paging is not None and not df_paging.empty:
        context["avg_swaps"] = (
            df_paging.get("pgpgin/s", pd.Series(0)).mean()
            + df_paging.get("pgpgout/s", pd.Series(0)).mean()
        )
        context["avg_majflt_s"] = df_paging.get("majflt/s", pd.Series(0)).mean()
        context["pswpin_total"] = df_paging.get("pswpin/s", pd.Series(0)).mean()
        context["pswpout_total"] = df_paging.get("pswpout/s", pd.Series(0)).mean()

    df_cswch = df_dict.get("sar_cswch")
    if df_cswch is not None and not df_cswch.empty:
        context["avg_cswch"] = df_cswch.get("cswch/s", pd.Series(0)).mean()
        context["avg_nvcswch_s"] = df_cswch.get("nvcswch/s", pd.Series(0)).mean()

    df_memory = df_dict.get("sar_memory")
    if df_memory is not None and not df_memory.empty:
        context["avg_memused_percent"] = df_memory.get("%memused", pd.Series(0)).mean()
        context["avg_commit_percent"] = df_memory.get("%commit", pd.Series(0)).mean()

    df_load = df_dict.get("sar_load")
    if df_load is not None and not df_load.empty:
        context["avg_load1"] = df_load.get("ldavg-1", pd.Series(0)).mean()

    df_network = df_dict.get("sar_network")
    if df_network is not None and not df_network.empty:
        context["avg_ifutil"] = df_network.get("%ifutil", pd.Series(0)).mean()

    if (perf_parsed := df_dict.get("perf_raw")) is not None and isinstance(
        perf_parsed, dict
    ):
        df_metrics = perf_parsed.get("metrics")
        if df_metrics is not None and not df_metrics.empty:
            metrics_avg = df_metrics.groupby("metric_name")["value"].mean().to_dict()
            context["tma_backend_bound"] = metrics_avg.get("backend_bound", 0.0)
            context["tma_frontend_bound"] = metrics_avg.get("frontend_bound", 0.0)
            context["tma_retiring"] = metrics_avg.get("retiring", 0.0)
            context["tma_bad_speculation"] = metrics_avg.get("bad_speculation", 0.0)
            context["tma_source_label"] = "perf -M (Official PMU Metrics)"
        else:
            context["tma_backend_bound"] = 0.0
            context["tma_frontend_bound"] = 0.0
            context["tma_retiring"] = 0.0
            context["tma_bad_speculation"] = 0.0
            context["tma_source_label"] = "Not Available"

    context.update(
        {
            "affinity_check_enabled": False,
            "affinity_leakage_count": 0,
            "affinity_absent_count": 0,
            "leakage_cores_str": "None",
            "absent_cores_str": "None",
        }
    )

    if expected_str and "cpu_features_df" in context:
        try:
            context["affinity_check_enabled"] = True
            expected_set = _parse_cpu_list_str(expected_str)
            df_features = context["cpu_features_df"]
            actual_busy_set = set(
                df_features[df_features["cluster_final"] == 1].index.astype(str)
            )
            if df_cpu is not None:
                df_all_cores = cast(pd.DataFrame, df_cpu[df_cpu["CPU"] != "all"].copy())
                if not df_all_cores.empty:
                    if "%user" in df_all_cores.columns:
                        df_all_cores["%total"] = (
                            df_all_cores["%user"] + df_all_cores["%system"]
                        )
                    else:
                        df_all_cores["%total"] = 0.0
                    all_core_means = df_all_cores.groupby("CPU")["%total"].mean()
                    all_busy_cores = set(
                        all_core_means[all_core_means > 15.0].index.astype(str)
                    )
                    leakage_set = all_busy_cores - expected_set
                    context["affinity_leakage_count"] = len(leakage_set)
                    if leakage_set:
                        context["leakage_cores_str"] = _format_cpu_list_to_range(
                            list(leakage_set)
                        )
            absent_set = expected_set - actual_busy_set
            context["affinity_absent_count"] = len(absent_set)
            if absent_set:
                context["absent_cores_str"] = _format_cpu_list_to_range(
                    list(absent_set)
                )
        except Exception as exc:  # pragma: no cover - defensive
            log.warning("Failed to validate CPU affinity: %s", exc)

    if expected_str and df_cpu is not None:
        target_set = _parse_cpu_list_str(expected_str)
        df_final_target = df_cpu[df_cpu["CPU"].isin(target_set)].copy()
        if not df_final_target.empty:
            if "%total" not in df_final_target.columns:
                df_final_target["%total"] = (
                    df_final_target["%user"] + df_final_target["%system"]
                )
            business_load = df_final_target["%total"].mean()
            context["total_cpu"] = business_load
            if "%iowait" in df_final_target.columns:
                context["avg_iowait"] = df_final_target["%iowait"].mean()
            log.info(
                "Decision Tree Logic Patched: total_cpu overridden to %.2f%% (Scope: %s)",
                business_load,
                expected_str,
            )

    return context
