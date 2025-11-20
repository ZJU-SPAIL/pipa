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

    # --- 2. 最终诊断引擎 (V4 - 直观版) ---

    # 初始化
    cpu_features["cluster_final"] = 0

    # 规则 A: 绝对空闲 (User + System < 10%)
    # 既然看 User+System，那就用它们的和来判断空闲
    # 注意：我们需要用到 mean_ 或 p95_，为了捕捉峰值，依然建议用 p95
    total_util_p95 = cpu_features["p95_%user"] + cpu_features["p95_%system"]

    IDLE_THRESHOLD = 10.0
    idle_mask = total_util_p95 < IDLE_THRESHOLD
    cpu_features.loc[idle_mask, "cluster_final"] = 99

    # 规则 B: 繁忙 (User + System > 15%)
    BUSY_THRESHOLD = 15.0
    busy_mask = total_util_p95 > BUSY_THRESHOLD

    cpu_features.loc[busy_mask, "cluster_final"] = 1

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
