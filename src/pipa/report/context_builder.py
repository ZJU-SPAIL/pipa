"""
上下文构建器模块

此模块构建包含规则引擎、绘图器和HTML模板所需的所有派生指标的综合上下文字典。
从原始数据计算各种性能指标和统计信息。
"""

import logging
from typing import Any, Dict, Optional, Set, cast

import pandas as pd

from src.pipa.report.cluster_analyzer import analyze_cpu_clusters
from src.utils import p95

log = logging.getLogger(__name__)


def _parse_cpu_list_str(cpu_list_str: str) -> Set[str]:
    """
    解析 Linux 格式的 CPU 列表字符串 (例如 "0-3,8,10-11") 为字符串集合。
    返回集合中的元素是字符串类型的 CPU ID (例如 {"0", "1", "2", "3", "8", "10", "11"})
    """
    cpus = set()
    if not cpu_list_str:
        return cpus

    cpu_list_str = cpu_list_str.strip()

    parts = cpu_list_str.split(",")
    for part in parts:
        part = part.strip()
        if "-" in part:
            try:
                start, end = map(int, part.split("-"))
                for i in range(start, end + 1):
                    cpus.add(str(i))
            except ValueError:
                continue
        else:
            if part.isdigit():
                cpus.add(part)
    return cpus


def _format_cpu_list_to_range(cpu_list: list) -> str:
    """
    将 [0, 1, 2, 4, 5] 转换为 "0-2,4-5" 的紧凑格式。
    """
    if not cpu_list:
        return "None"
    try:
        sorted_cpus = sorted([int(c) for c in cpu_list])
    except ValueError:
        return ",".join(map(str, cpu_list))

    if not sorted_cpus:
        return "None"

    ranges = []
    range_start = sorted_cpus[0]
    for i in range(1, len(sorted_cpus)):
        if sorted_cpus[i] > sorted_cpus[i - 1] + 1:
            if range_start == sorted_cpus[i - 1]:
                ranges.append(str(range_start))
            else:
                ranges.append(f"{range_start}-{sorted_cpus[i-1]}")
            range_start = sorted_cpus[i]

    if range_start == sorted_cpus[-1]:
        ranges.append(str(range_start))
    else:
        ranges.append(f"{range_start}-{sorted_cpus[-1]}")

    return ",".join(ranges)


def build_full_context(
    df_dict: Dict[str, pd.DataFrame], static_info: Dict[str, Any], rule_configs: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    构建包含规则引擎、绘图器和HTML模板所需的所有派生指标的综合上下文字典。

    从DataFrame字典和静态系统信息中计算各种性能指标，
    包括CPU利用率、缓存命中率、I/O统计等。

    参数:
        df_dict: 包含各种性能数据的DataFrame字典。
        static_info: 系统的静态配置信息字典。

    返回:
        包含所有计算指标的上下文字典。
    """
    # 初始化上下文字典，包含所有可能的指标，默认值为0
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
        # NUMA 相关默认值
        "is_numa_imbalanced": False,
        "numa_nodes_count": 1,
        "numa_max_diff": 0.0,
        "numa_status_msg": "Non-NUMA or Single Node",
        "iowait_core_count": 0,  # 初始化
        # 规则引擎使用的安全默认值，防止缺键导致评估失败
        "is_cpu_imbalanced": False,
        # 磁盘相关默认值
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
        # 网络相关默认值
        "avg_ifutil": 0.0,
        # 阈值展示默认值
        "effective_await_threshold": 0.0,
    }

    # 从静态信息中获取CPU数量
    if static_info and (cpu_info := static_info.get("cpu_info")):
        context["num_cpu"] = cpu_info.get("CPU(s)", 1)

    # 提前初始化 expected_str，防止后面 Pylance 报 unbound variable
    expected_str = rule_configs.get("expected_cpus_str") if rule_configs else None

    df_cpu = df_dict.get("sar_cpu")
    # Ensure df_per_core is always defined to avoid "possibly unbound" warnings/errors
    df_per_core = pd.DataFrame()
    if df_cpu is not None and not df_cpu.empty:

        # === 核心逻辑变更：确定计算范围 ===
        # 默认使用所有核心
        # 显式 cast 为 DataFrame，消除 Pylance 类型报错
        df_per_core = cast(pd.DataFrame, df_cpu[df_cpu["CPU"] != "all"].copy())

        target_cpus = None

        # 2. 如果过滤后还有数据，进行聚合计算
        if not df_per_core.empty:
            if "%user" in df_per_core.columns and "%system" in df_per_core.columns:
                df_per_core["%total"] = df_per_core["%user"] + df_per_core["%system"]
            else:
                df_per_core["%total"] = 0.0

            # 3. 集群分析 (只针对过滤后的核心)
            # 这样就不会因为那 64 个空闲核而报“负载不均”了
            # df_per_core 已经通过 cast 确保是 DataFrame，Pylance 不会再报错
            clustering_results = analyze_cpu_clusters(df_per_core, config=rule_configs)
            if clustering_results:
                context.update(clustering_results)

                # === 逻辑：计算负载不均标志位 ===
                # 逻辑：如果有多个“部落”，且其中至少有一个是“繁忙”的，那就叫负载不均
                clusters_summary = context.get("cpu_clusters_summary", [])
                is_imbalanced = False

                if len(clusters_summary) > 1:
                    # 检查是否存在 Busy (ID=1) 的集群
                    # cluster_analyzer 返回的 summary 里有 'id' 字段
                    has_busy = any(c.get("id") == 1 for c in clusters_summary)
                    if has_busy:
                        is_imbalanced = True

                context["is_cpu_imbalanced"] = is_imbalanced
                # ============================================

            # 4. 计算统计指标 (Mean, P95, Max)
            core_utils = df_per_core.groupby("CPU").agg({"%total": "mean", "%iowait": ["mean", p95, "max"]})

            context["cpu_util_std_dev"] = core_utils[("%total", "mean")].std()
            context["cpu_max_util"] = core_utils[("%total", "mean")].max()
            context["cpu_min_util"] = core_utils[("%total", "mean")].min()

            if ("%iowait", "p95") in core_utils.columns:
                context["p95_single_core_iowait"] = core_utils[("%iowait", "p95")].max()
                context["max_single_core_iowait"] = core_utils[("%iowait", "max")].max()

                # 计算受灾核心数及详情 (White-box Evidence)
                io_wait_threshold = rule_configs.get("IO_WAIT_HIGH_THRESHOLD", 10.0) if rule_configs else 10.0
                high_iowait_series = core_utils[("%iowait", "p95")]

                # 筛选出超标的核心
                bad_cores = high_iowait_series[high_iowait_series > io_wait_threshold]
                context["iowait_core_count"] = len(bad_cores)

                # 生成更具洞察力的详情字符串
                if not bad_cores.empty:
                    # 1. 基础范围字符串
                    # 注意：index 可能是字符串，需转 int 排序
                    sorted_bad_cpus = sorted([int(c) for c in bad_cores.index])
                    affected_range = _format_cpu_list_to_range(sorted_bad_cpus)

                    # 2. [NEW] 寻找“重灾区” (Largest Contiguous Block)
                    # 算法：找出最长的一段连续核心，计算其平均压力
                    longest_seq = []
                    current_seq = []
                    if sorted_bad_cpus:
                        current_seq = [sorted_bad_cpus[0]]
                        for i in range(1, len(sorted_bad_cpus)):
                            if sorted_bad_cpus[i] == sorted_bad_cpus[i - 1] + 1:
                                current_seq.append(sorted_bad_cpus[i])
                            else:
                                if len(current_seq) > len(longest_seq):
                                    longest_seq = current_seq
                                current_seq = [sorted_bad_cpus[i]]
                        # 检查最后一段
                        if len(current_seq) > len(longest_seq):
                            longest_seq = current_seq

                    zone_desc = ""
                    # 只有当重灾区包含超过 4 个核心时才显示，避免和 Top3 重复
                    if len(longest_seq) > 4:
                        # 计算该区域的平均 iowait
                        # 需要把 int 转回 str 来索引 Series
                        seq_indices = [str(c) for c in longest_seq]
                        # 过滤出存在于 bad_cores 里的索引 (理论上都在，加上防止报错)
                        valid_indices = [i for i in seq_indices if i in bad_cores.index]
                        if valid_indices:
                            zone_avg = bad_cores.loc[valid_indices].mean()
                            zone_str = f"{longest_seq[0]}-{longest_seq[-1]}"
                            zone_desc = f"; 重灾区: {zone_str} (均值 {zone_avg:.1f}%)"

                    # 3. 提取 Top 3 最惨的核心
                    top_bad = bad_cores.sort_values(ascending=False).head(3)
                    top_details = [f"CPU {cpu}={val:.1f}%" for cpu, val in top_bad.items()]
                    top_str = ", ".join(top_details)

                    # 4. 组合输出
                    # 格式: "范围: 0-63; 重灾区: 32-47 (均值 18.2%); Top3: ..."
                    context["iowait_core_details"] = f"范围: {affected_range}{zone_desc}; Top3: {top_str}"
                else:
                    context["iowait_core_details"] = "无"

            # === 5. [关键修正] 重算全局指标 ===
            # 如果指定了范围，TOTAL CPU 应该是这几个核的平均值，而不是全系统的平均值
            if target_cpus:
                context["total_cpu"] = df_per_core["%total"].mean()
                if "%iowait" in df_per_core.columns:
                    context["avg_iowait"] = df_per_core["%iowait"].mean()
            else:
                # 如果没指定范围，回退到 sar 提供的 'all' 行 (或者手动算全核平均)
                df_cpu_all = df_cpu[df_cpu["CPU"] == "all"]
                if not df_cpu_all.empty:
                    context["total_cpu"] = (
                        df_cpu_all.get("%user", pd.Series(0)).mean() + df_cpu_all.get("%system", pd.Series(0)).mean()
                    )
                    context["avg_iowait"] = df_cpu_all.get("%iowait", pd.Series(0)).mean()
                    context["avg_irq_percent"] = df_cpu_all.get("%irq", pd.Series(0)).mean()
                    context["avg_softirq_percent"] = df_cpu_all.get("%soft", pd.Series(0)).mean()

            # === 6. NUMA 分析 (基于过滤后的核心) ===
            numa_info = static_info.get("numa_info", {}) if static_info else {}
            numa_topology = numa_info.get("numa_topology", {})

            if numa_topology and len(numa_topology) > 1:
                # [新增] 创建一个给前端JS使用的NUMA映射表
                context["numa_cpu_map"] = {
                    node_name.replace("node", "numa_node_"): cpu_list_str
                    for node_name, cpu_list_str in numa_topology.items()
                }
                context["numa_nodes_count"] = len(numa_topology)
                cpu_to_node = {}
                for node_name, cpu_list_str in numa_topology.items():
                    cpu_set = _parse_cpu_list_str(str(cpu_list_str))
                    for cpu_id in cpu_set:
                        cpu_to_node[cpu_id] = node_name

                df_per_core["NUMA_Node"] = df_per_core["CPU"].map(cpu_to_node)

                # 只统计在这个 Profile 里涉及到的 NUMA 节点
                node_stats = df_per_core.groupby("NUMA_Node")["%total"].mean()

                if not node_stats.empty:
                    min_node_util = node_stats.min()
                    max_node_util = node_stats.max()
                    context["numa_max_diff"] = max_node_util - min_node_util

                    status_parts = []
                    for node, util in node_stats.items():
                        status_parts.append(f"{node}: <strong>{util:.1f}%</strong>")
                    context["numa_status_msg"] = ", ".join(status_parts)

        # [新增逻辑] 如果用户指定了绑核，则额外计算一个 workload_avg 并注入回 sar_cpu
        if target_cpus and not df_per_core.empty:
            # 按时间戳聚合，计算业务核心的平均值
            workload_avg_df = df_per_core.groupby("timestamp").mean(numeric_only=True).reset_index()
            workload_avg_df["CPU"] = "workload_avg"

            # --- 核心修复：补上缺失的元数据列 ---
            # 从原始 df_cpu 的第一行获取 hostname 和 interval
            # 因为 df_cpu 在这个代码块之前已经确认存在且非空，所以 iloc[0] 是安全的
            first_row = df_cpu.iloc[0]
            workload_avg_df["hostname"] = first_row["hostname"]
            workload_avg_df["interval"] = first_row["interval"]

            # 确保列的顺序和原始 df_cpu 完全一致
            cols_order = df_cpu.columns.tolist()
            workload_avg_df = workload_avg_df[cols_order]
            # --- 修复结束 ---

            # 将新的聚合数据合并回原始的 sar_cpu DataFrame
            df_dict["sar_cpu"] = pd.concat([df_cpu, workload_avg_df], ignore_index=True)
            log.info("Injected 'workload_avg' series into sar_cpu data for business-centric view.")
    # --- 后续通用指标 (I/O, Memory, Network) ---
    df_io = df_dict.get("sar_io")
    if df_io is not None and not df_io.empty:
        context["total_tps"] = df_io.get("tps", pd.Series(0)).sum()
        context["avg_await"] = df_io.get("await", pd.Series(0)).mean()
        context["avg_util"] = df_io.get("%util", pd.Series(0)).mean()
        context["avg_avgrq_sz"] = df_io.get("avgrq-sz", pd.Series(0)).mean()
        context["avg_avgqu_sz"] = df_io.get("avgqu-sz", pd.Series(0)).mean()

    df_disk = df_dict.get("sar_disk")
    context["max_disk_util"] = 0.0
    context["max_disk_await"] = 0.0
    context["busiest_disk_name"] = "None"
    context["avg_avgrq_sz_kb"] = 0.0
    context["avg_avgqu_sz"] = 0.0
    context["disk_throughput_mb"] = 0.0
    context["busiest_disk_subtype"] = "Unknown"

    if df_disk is not None and not df_disk.empty:
        valid_disks = df_disk[~df_disk["DEV"].str.contains("loop|ram|zram")]
        if not valid_disks.empty:
            numeric_cols = valid_disks.select_dtypes(include=["number"]).columns
            disk_stats = valid_disks.groupby("DEV")[numeric_cols].agg(["mean", "max", p95])

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

                qu_col = "aqu-sz" if ("aqu-sz", "mean") in stats.index else "avgqu-sz"
                context["avg_avgqu_sz"] = stats.get((qu_col, "mean"), 0.0)
                context["max_avgqu_sz"] = stats.get((qu_col, "max"), 0.0)
                context["p95_avgqu_sz"] = stats.get((qu_col, "p95"), 0.0)

                sz_col = "areq-sz" if ("areq-sz", "mean") in stats.index else "avgrq-sz"
                context["avg_avgrq_sz_kb"] = stats.get((sz_col, "mean"), 0.0) / 2.0

                context["disk_rkB_s"] = stats.get(("rkB/s", "mean"), 0.0)
                context["disk_wkB_s"] = stats.get(("wkB/s", "mean"), 0.0)
                context["disk_throughput_mb"] = (context["disk_rkB_s"] + context["disk_wkB_s"]) / 1024.0

            if static_info and "disk_info" in static_info:
                devices = static_info["disk_info"].get("block_devices", [])
                for d in devices:
                    if d.get("name") == busiest_dev or any(
                        p.get("name") == busiest_dev for p in d.get("partitions", [])
                    ):
                        context["busiest_disk_type"] = d.get("rotational", "Unknown")
                        break

            disk_type = context.get("busiest_disk_type", "Unknown")
            disk_name = str(context.get("busiest_disk_name", ""))
            if disk_type == "HDD":
                context["busiest_disk_subtype"] = "HDD"
            elif disk_type == "SSD":
                context["busiest_disk_subtype"] = "NVME_SSD" if "nvme" in disk_name else "SATA_SSD"

            effective_threshold = 0.0
            subtype = context.get("busiest_disk_subtype")
            if subtype == "SATA_SSD":
                effective_threshold = rule_configs.get("IO_AWAIT_SATA_SSD_THRESHOLD", 0.0) if rule_configs else 5.0
            elif subtype == "NVME_SSD":
                effective_threshold = rule_configs.get("IO_AWAIT_NVME_SSD_THRESHOLD", 0.0) if rule_configs else 1.0
            elif subtype == "HDD":
                effective_threshold = rule_configs.get("IO_AWAIT_HDD_THRESHOLD", 0.0) if rule_configs else 30.0
            context["effective_await_threshold"] = effective_threshold

    df_paging = df_dict.get("sar_paging")
    if df_paging is not None and not df_paging.empty:
        context["avg_swaps"] = (
            df_paging.get("pgpgin/s", pd.Series(0)).mean() + df_paging.get("pgpgout/s", pd.Series(0)).mean()
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

    if (perf_parsed := df_dict.get("perf_raw")) is not None and isinstance(perf_parsed, dict):
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

    # CPU Affinity check variables
    context["affinity_check_enabled"] = False
    context["affinity_leakage_count"] = 0
    context["affinity_absent_count"] = 0
    context["leakage_cores_str"] = "None"
    context["absent_cores_str"] = "None"

    if expected_str and "cpu_features_df" in context:
        try:
            context["affinity_check_enabled"] = True
            expected_set = _parse_cpu_list_str(expected_str)
            df_features = context["cpu_features_df"]

            # 这里的 actual_busy_set 是指在“预期范围内”忙碌的核心
            actual_busy_set = set(df_features[df_features["cluster_final"] == 1].index.astype(str))

            # [FIX Logic] 为了审计 Leakage，我们需要回溯去查原始 df_cpu
            if df_cpu is not None:
                # 重新计算一次全量的状态，仅用于审计
                df_all_cores = cast(pd.DataFrame, df_cpu[df_cpu["CPU"] != "all"].copy())
                if not df_all_cores.empty:
                    if "%user" in df_all_cores.columns:
                        df_all_cores["%total"] = df_all_cores["%user"] + df_all_cores["%system"]
                    else:
                        df_all_cores["%total"] = 0.0

                    # 简单判定：均值 > 15% 算忙
                    all_core_means = df_all_cores.groupby("CPU")["%total"].mean()
                    all_busy_cores = set(all_core_means[all_core_means > 15.0].index.astype(str))

                    # 计算 Leakage: 全局忙 减去 预期
                    leakage_set = all_busy_cores - expected_set
                    context["affinity_leakage_count"] = len(leakage_set)
                    if leakage_set:
                        context["leakage_cores_str"] = _format_cpu_list_to_range(list(leakage_set))

            # 计算 Absent: 预期 减去 (预期范围内的实际忙)
            absent_set = expected_set - actual_busy_set
            context["affinity_absent_count"] = len(absent_set)
            if absent_set:
                context["absent_cores_str"] = _format_cpu_list_to_range(list(absent_set))

        except Exception as e:
            print(f"Warning: Failed to validate CPU affinity: {e}")

    # ==============================================================================
    # 2. [修复] 注入 workload_avg (仅包含预期核心的平均值)
    # 这对于前端绘图很有用，显示“我的业务平均负载” vs “整机负载”
    # ==============================================================================
    if expected_str and df_cpu is not None:
        # 1. 解析目标核心
        expected_set = _parse_cpu_list_str(expected_str)

        # 2. 从全量数据中筛选出业务核心
        df_per_core = cast(pd.DataFrame, df_cpu[df_cpu["CPU"] != "all"].copy())
        df_workload = df_per_core[df_per_core["CPU"].isin(expected_set)]

        if not df_workload.empty:
            # 3. 按时间戳计算平均值
            workload_avg_df = df_workload.groupby("timestamp").mean(numeric_only=True).reset_index()
            workload_avg_df["CPU"] = "workload_avg"

            # 4. 补全元数据
            first_row = df_cpu.iloc[0]
            workload_avg_df["hostname"] = first_row.get("hostname", "unknown")
            workload_avg_df["interval"] = first_row.get("interval", 1)

            # 5. 确保列顺序一致
            cols_to_use = [c for c in df_cpu.columns if c in workload_avg_df.columns]
            workload_avg_df = workload_avg_df[cols_to_use]

            # 6. 注入回 sar_cpu
            df_final = pd.concat([df_cpu, workload_avg_df], ignore_index=True)
            df_dict["sar_cpu"] = df_final
            log.info(f"Injected 'workload_avg' series for CPUs: {expected_str}")

    # ==============================================================================
    # 强制覆盖决策树指标：只看业务核心
    # 无论前面算了什么，这里最后再算一遍业务核心的利用率，并覆盖 total_cpu
    # ==============================================================================
    if expected_str and df_cpu is not None:
        # 1. 重新解析目标核心
        target_set = _parse_cpu_list_str(expected_str)

        # 2. 从 df_cpu (最原始的数据) 中筛选，只保留业务核心
        # isin 自动会排除 'all' 和 'workload_avg'
        df_final_target = df_cpu[df_cpu["CPU"].isin(target_set)].copy()

        if not df_final_target.empty:
            # 3. 确保有 %total 列 (以防万一)
            if "%total" not in df_final_target.columns:
                df_final_target["%total"] = df_final_target["%user"] + df_final_target["%system"]

            # 4. 计算均值
            business_load = df_final_target["%total"].mean()

            # 5. 【核心动作】 强制覆盖 context
            context["total_cpu"] = business_load

            # 6. 顺便修正 iowait
            if "%iowait" in df_final_target.columns:
                context["avg_iowait"] = df_final_target["%iowait"].mean()

            # 打个日志证明我改了
            log.info(
                f"Decision Tree Logic Patched: total_cpu overridden to {business_load:.2f}% (Scope: {expected_str})"
            )

    return context
