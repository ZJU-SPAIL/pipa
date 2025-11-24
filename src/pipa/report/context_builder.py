"""
上下文构建器模块

此模块构建包含规则引擎、绘图器和HTML模板所需的所有派生指标的综合上下文字典。
从原始数据计算各种性能指标和统计信息。
"""

from typing import Any, Dict, Set

import pandas as pd

from src.pipa.report.cluster_analyzer import analyze_cpu_clusters


def _parse_cpu_list_str(cpu_list_str: str) -> Set[str]:
    """
    解析 Linux 格式的 CPU 列表字符串 (例如 "0-3,8,10-11") 为字符串集合。
    返回集合中的元素是字符串类型的 CPU ID (例如 {"0", "1", "2", "3", "8", "10", "11"})
    """
    cpus = set()
    if not cpu_list_str:
        return cpus

    # 移除可能存在的空白字符
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


def build_full_context(df_dict: Dict[str, pd.DataFrame], static_info: Dict[str, Any]) -> Dict[str, Any]:
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
    }

    # 从静态信息中获取CPU数量
    if static_info and (cpu_info := static_info.get("cpu_info")):
        context["num_cpu"] = cpu_info.get("CPU(s)", 1)

    df_cpu = df_dict.get("sar_cpu")
    if df_cpu is not None and not df_cpu.empty:
        clustering_results = analyze_cpu_clusters(df_cpu)
        if clustering_results:
            context.update(clustering_results)

        # 2. 预处理：计算 %total 利用率
        df_per_core = df_cpu[df_cpu["CPU"] != "all"].copy()
        if not df_per_core.empty:
            # 计算总利用率（用户+系统）
            if "%user" in df_per_core.columns and "%system" in df_per_core.columns:
                df_per_core["%total"] = df_per_core["%user"] + df_per_core["%system"]
            else:
                df_per_core["%total"] = 0.0

            # 计算每核心的平均利用率
            core_avg_utils = df_per_core.groupby("CPU")["%total"].mean()

            # 计算利用率的统计指标
            context["cpu_util_std_dev"] = core_avg_utils.std()
            context["cpu_max_util"] = core_avg_utils.max()
            context["cpu_min_util"] = core_avg_utils.min()

            # === 4. 新增：NUMA 负载均衡分析 ===
            numa_info = static_info.get("numa_info", {}) if static_info else {}
            numa_topology = numa_info.get("numa_topology", {})

            # 只有当存在拓扑信息且节点数 > 1 时才分析
            if numa_topology and len(numa_topology) > 1:
                context["numa_nodes_count"] = len(numa_topology)

                # 构建 CPU -> Node 的映射表
                cpu_to_node = {}
                for node_name, cpu_list_str in numa_topology.items():
                    cpu_set = _parse_cpu_list_str(str(cpu_list_str))
                    for cpu_id in cpu_set:
                        cpu_to_node[cpu_id] = node_name

                # 将每个核心的数据映射到 NUMA 节点
                # 注意：df_per_core["CPU"] 是字符串类型，map 需要匹配
                df_per_core["NUMA_Node"] = df_per_core["CPU"].map(cpu_to_node)

                # 计算每个节点的平均利用率
                node_stats = df_per_core.groupby("NUMA_Node")["%total"].mean()

                if not node_stats.empty:
                    min_node_util = node_stats.min()
                    max_node_util = node_stats.max()
                    max_diff = max_node_util - min_node_util

                    context["numa_max_diff"] = max_diff

                    # 生成详细的节点状态描述字符串
                    # 例如: "node0: 85.2%, node1: 12.4%"
                    status_parts = []
                    for node, util in node_stats.items():
                        status_parts.append(f"{node}: <strong>{util:.1f}%</strong>")
                    context["numa_status_msg"] = ", ".join(status_parts)

                    # 标记是否不均衡 (阈值将在 Rules 中定义，这里只提供数据，或者预判)
                    # 这里我们预置一个 flag，方便前端或简单逻辑使用，
                    # 但核心判定还是交给 rules/decision_tree.yaml
                    pass

        # 处理聚合的CPU数据 (CPU == "all")
        df_cpu_all = df_cpu[df_cpu["CPU"] == "all"]
        if not df_cpu_all.empty:
            # 计算总CPU利用率
            context["total_cpu"] = (
                df_cpu_all.get("%user", pd.Series(0)).mean() + df_cpu_all.get("%system", pd.Series(0)).mean()
            )
            # 计算中断相关的指标
            context["avg_irq_percent"] = df_cpu_all.get("%irq", pd.Series(0)).mean()
            context["avg_softirq_percent"] = df_cpu_all.get("%soft", pd.Series(0)).mean()
            context["avg_iowait"] = df_cpu_all.get("%iowait", pd.Series(0)).mean()

    # 处理I/O数据：计算各种I/O性能指标
    df_io = df_dict.get("sar_io")
    if df_io is not None and not df_io.empty:
        context["total_tps"] = df_io.get("tps", pd.Series(0)).sum()
        context["avg_await"] = df_io.get("await", pd.Series(0)).mean()
        context["avg_util"] = df_io.get("%util", pd.Series(0)).mean()
        context["avg_avgrq_sz"] = df_io.get("avgrq-sz", pd.Series(0)).mean()
        context["avg_avgqu_sz"] = df_io.get("avgqu-sz", pd.Series(0)).mean()
        context["avg_bread_s"] = df_io.get("bread/s", pd.Series(0)).mean()
        context["avg_bwrtn_s"] = df_io.get("bwrtn/s", pd.Series(0)).mean()

    # 处理分页数据：计算交换和页面错误指标
    df_paging = df_dict.get("sar_paging")
    if df_paging is not None and not df_paging.empty:
        context["avg_swaps"] = (
            df_paging.get("pgpgin/s", pd.Series(0)).mean() + df_paging.get("pgpgout/s", pd.Series(0)).mean()
        )
        context["avg_majflt_s"] = df_paging.get("majflt/s", pd.Series(0)).mean()

    # 处理上下文切换数据
    df_cswch = df_dict.get("sar_cswch")
    if df_cswch is not None and not df_cswch.empty:
        context["avg_cswch"] = df_cswch.get("cswch/s", pd.Series(0)).mean()
        context["avg_nvcswch_s"] = df_cswch.get("nvcswch/s", pd.Series(0)).mean()

    # 处理内存数据：计算内存使用率和缓存指标
    df_memory = df_dict.get("sar_memory")
    if df_memory is not None and not df_memory.empty:
        context["avg_memused_percent"] = df_memory.get("%memused", pd.Series(0)).mean()
        context["avg_commit_percent"] = df_memory.get("%commit", pd.Series(0)).mean()
        context["avg_kbcached"] = df_memory.get("kbcached", pd.Series(0)).mean()
        context["avg_kbactive"] = df_memory.get("kbactive", pd.Series(0)).mean()

    # 处理负载数据
    df_load = df_dict.get("sar_load")
    if df_load is not None and not df_load.empty:
        context["avg_load1"] = df_load.get("ldavg-1", pd.Series(0)).mean()

    # 处理网络数据：计算网络吞吐量和利用率
    df_network = df_dict.get("sar_network")
    if df_network is not None and not df_network.empty:
        context["avg_rxkB_s"] = df_network.get("rxkB/s", pd.Series(0)).mean()
        context["avg_txkB_s"] = df_network.get("txkB/s", pd.Series(0)).mean()
        context["avg_ifutil"] = df_network.get("%ifutil", pd.Series(0)).mean()

    # 处理 perf 数据 (Parser returns dict with 'events' and 'metrics' DataFrames)
    # 从 analyze.py 传过来的是 "perf_raw" 这个键，对应 parser 返回的字典
    if (perf_parsed := df_dict.get("perf_raw")) is not None and isinstance(perf_parsed, dict):

        # === 1. 处理 Metrics (用于 TMA) ===
        # 获取 metrics DataFrame
        df_metrics = perf_parsed.get("metrics")
        if df_metrics is not None and not df_metrics.empty:
            # 计算所有核心的平均值
            # 注意：我们的 parser 已经把值转成了 float，且 metric_name 是标准化的
            metrics_avg = df_metrics.groupby("metric_name")["value"].mean().to_dict()

            # 映射 TMA 指标 (带默认值)
            context["tma_backend_bound"] = metrics_avg.get("backend_bound", 0.0)
            context["tma_frontend_bound"] = metrics_avg.get("frontend_bound", 0.0)
            context["tma_retiring"] = metrics_avg.get("retiring", 0.0)
            context["tma_bad_speculation"] = metrics_avg.get("bad_speculation", 0.0)

            context["tma_source_label"] = "perf -M (Official PMU Metrics)"

            # 构造前端显示用的数据对象 (不再需要 slots/cycles 等原始数据，因为是直接 metric)
            context["tma_data"] = {
                "source": "perf_metrics",
                "pct_backend": context["tma_backend_bound"],
                "pct_frontend": context["tma_frontend_bound"],
                "pct_retiring": context["tma_retiring"],
                "pct_badspec": context["tma_bad_speculation"],
                # 为了模板兼容，给一些 dummy 值，或者修改模板不显示它们
                "cycles": 0,
                "slots": 0,
                "instructions": 0,
                "frontend_cycles": 0,
                "bad_spec_penalty": 0,
            }
        else:
            # 没有 metrics，全置 0
            context["tma_backend_bound"] = 0.0
            context["tma_frontend_bound"] = 0.0
            context["tma_retiring"] = 0.0
            context["tma_bad_speculation"] = 0.0
            context["tma_source_label"] = "Not Available (No PMU Metrics)"
            context["tma_data"] = None

        # === 2. 处理 Events (用于 IPC, Cache, CSWCH 等) ===
        # 获取 events DataFrame
        df_events = perf_parsed.get("events")
        if df_events is not None and not df_events.empty:
            # 为了方便，只看 system-wide (cpu=='all') 的数据
            # 注意：如果采集时用了 -A，df 里会有具体的 CPU 号，我们需要先聚合
            df_events_all = df_events.groupby("event_name")["value"].sum()  # 或者 mean，取决于指标性质
            # 对于 cycles/instructions 这种累加值，如果是 -A 采集的，应该 sum；如果是 -a 采集的(cpu='all')，直接取。
            # 既然我们解析器里处理了 'all'，我们这里简单处理：

            # 辅助函数：安全获取值
            def get_val(name):
                # 尝试精确匹配
                if name in df_events_all:
                    return df_events_all[name].item()  # 获取标量值
                return 0.0

            # 计算分支预测
            branch_inst = get_val("branch-instructions")
            branch_miss = get_val("branch-misses")
            if branch_inst > 0:
                context["branch_miss_rate"] = (branch_miss / branch_inst) * 100

            # 计算 L3 Cache
            llc_loads = get_val("LLC-loads") + get_val("ll_cache_rd")
            llc_misses = get_val("LLC-load-misses") + get_val("ll_cache_miss_rd")
            if llc_loads > 0:
                context["l3_cache_miss_rate"] = (llc_misses / llc_loads) * 100

            # 计算 IPC
            insts = get_val("instructions") + get_val("inst_retired.any")
            cycles = get_val("cycles") + get_val("cpu-cycles")
            if cycles > 0:
                context["ipc"] = insts / cycles

            # 计算 CSWCH
            context["avg_cswch"] = get_val("context-switches")

    is_imbalanced = False
    clusters_summary = context.get("cpu_clusters_summary", [])

    if clusters_summary:
        BUSY_THRESHOLD_P95_USER_SYS = 15.0

        is_busy_cluster_found = any(c.get("id") == 1 for c in clusters_summary)

        # 备用逻辑：检查 Cluster 0 是否有高负载
        # 改为: p95_user + p95_system > 15
        is_active_cluster_busy = any(
            c.get("id") == 0 and (c.get("p95_%user", 0) + c.get("p95_%system", 0)) > BUSY_THRESHOLD_P95_USER_SYS
            for c in clusters_summary
        )

        if is_busy_cluster_found or is_active_cluster_busy:
            is_imbalanced = True

    context["is_cpu_imbalanced"] = is_imbalanced

    # 转换百分比格式
    if "HIGH_LOAD_AVG_RATIO_TO_CPU" in context:
        context["high_load_avg_ratio_to_cpu_percent"] = context["HIGH_LOAD_AVG_RATIO_TO_CPU"] * 100

    return context
