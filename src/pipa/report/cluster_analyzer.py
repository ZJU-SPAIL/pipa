# src/pipa/report/cluster_analyzer.py

import logging
from typing import Any, Dict

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

log = logging.getLogger(__name__)


def analyze_cpu_clusters(df_sar_cpu: pd.DataFrame) -> Dict[str, Any]:
    """
    对 per-core CPU 数据执行基于物理规则的分类分析 (V4 - 物理感知修正版)。
    虽然名为“聚类”，但实际上采用了更符合系统物理特性的阈值分层策略，
    同时保留 K-Distance 计算用于展示数据分布特性。
    """
    if df_sar_cpu is None or df_sar_cpu.empty:
        return {}

    log.info("Starting CPU core behavior analysis (V4 Physics-Aware Engine)...")

    # --- 1. 特征工程 ---
    df_per_core = df_sar_cpu[df_sar_cpu["CPU"] != "all"].copy()
    if df_per_core.empty:
        log.warning("No per-core CPU data found for clustering.")
        return {}

    def p95(x):
        return x.quantile(0.95)

    features_to_aggregate = ["%user", "%system", "%iowait", "%idle"]
    cpu_features = df_per_core.groupby("CPU")[features_to_aggregate].agg(["mean", p95])
    cpu_features.columns = [f"{agg}_{col}" for col, agg in cpu_features.columns]

    # 我们依然需要做 Scaling，为了画散点图和算 K-Distance
    features_to_cluster = ["mean_%user", "mean_%system", "mean_%iowait", "mean_%idle", "p95_%user", "p95_%system"]
    features_to_cluster = [f for f in features_to_cluster if f in cpu_features.columns]

    if len(cpu_features) < 4:
        log.warning("Not enough CPU cores to perform analysis.")
        return {}

    scaler = StandardScaler()
    cpu_features_scaled = scaler.fit_transform(cpu_features.reindex(columns=features_to_cluster).fillna(0))

    # --- 2. 最终诊断引擎 (V4 - 物理感知修正版) ---

    # 初始化：默认为 0 (中间态/未知)
    # 如果有核心恰好卡在 10% - 15% 之间，它会保留为 0，这很合理
    cpu_features["cluster_final"] = 0

    # 规则 A (强力清洗): 定义“绝对空闲”
    # 物理意义：如果一个核心 90% 的时间都在睡觉 (P95 Idle > 90%)，那它就是 Idle。
    # 这能有效合并 99.9% 和 95% 的核心到同一类。
    ABS_IDLE_THRESHOLD = 90.0

    idle_mask = cpu_features["p95_%idle"] > ABS_IDLE_THRESHOLD
    cpu_features.loc[idle_mask, "cluster_final"] = 99  # 标记: Idle (部落 99)

    # 规则 B (识别瓶颈): 定义“繁忙”
    # 物理意义：只要不闲着的时间 (100 - Idle) 超过阈值，就是繁忙。
    # 这涵盖了 User 高、System 高、Softirq 高等所有忙碌情况。
    BUSY_THRESHOLD = 15.0

    # 注意逻辑顺序：我们只把“非空闲”的标记为繁忙。
    # 实际上 (100 - p95_idle) > 15 等价于 p95_idle < 85。
    # 这与上面的 > 90 是天然互斥的，不会打架。
    busy_mask = (100.0 - cpu_features["p95_%idle"]) > BUSY_THRESHOLD

    cpu_features.loc[busy_mask, "cluster_final"] = 1  # 标记: Busy (部落 1)

    # --- 3. 生成摘要 (用于报告和决策树) ---
    final_stats = cpu_features.groupby("cluster_final").mean().round(2)
    final_counts = cpu_features["cluster_final"].value_counts()

    clusters_summary = []
    for cluster_id in final_stats.index:
        stats = final_stats.loc[cluster_id]
        summary = stats.to_dict()
        summary["id"] = int(cluster_id)
        summary["count"] = int(final_counts.loc[cluster_id])
        clusters_summary.append(summary)

    log.info(f"Analysis complete. Found {len(final_stats)} groups (0=Mid, 1=Busy, 99=Idle).")

    # --- 4. 辅助数据 (用于图表展示) ---
    # 我们依然计算 K-Distance，作为数据分布的参考（虽然不用于分类了）
    k = 4
    neighbors = NearestNeighbors(n_neighbors=k).fit(cpu_features_scaled)
    distances, _ = neighbors.kneighbors(cpu_features_scaled)
    k_distances = np.sort(distances[:, k - 1], axis=0)

    return {
        "cpu_clusters_summary": clusters_summary,
        "cpu_clusters_count": len(final_stats),
        "cpu_features_df": cpu_features,
        "knee_distances": k_distances,
        "optimal_eps": 0.20,  # 固定值作为展示
    }
