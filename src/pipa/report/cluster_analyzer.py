"""CPU cluster analysis helpers."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import pandas as pd

log = logging.getLogger(__name__)


def analyze_cpu_clusters(
    df_sar_cpu: pd.DataFrame, config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Classify per-core CPU behavior using deterministic thresholds."""

    cfg = config or {}
    idle_threshold = cfg.get("CPU_CLUSTER_IDLE_THRESHOLD", 10.0)
    busy_threshold = cfg.get("CPU_CLUSTER_BUSY_THRESHOLD", 15.0)

    if df_sar_cpu is None or df_sar_cpu.empty:
        return {}

    log.info("Starting CPU core behavior analysis (V4 Physics-Aware Engine)...")
    df_per_core = df_sar_cpu[df_sar_cpu["CPU"] != "all"].copy()
    if df_per_core.empty:
        log.warning("No per-core CPU data found for clustering.")
        return {}

    def p95(values: pd.Series) -> float:
        return values.quantile(0.95)

    features_to_aggregate = ["%user", "%system", "%iowait", "%idle"]
    cpu_features = df_per_core.groupby("CPU")[features_to_aggregate].agg(["mean", p95])
    cpu_features.columns = [f"{agg}_{col}" for col, agg in cpu_features.columns]

    if len(cpu_features) < 4:
        log.warning("Not enough CPU cores to perform analysis.")
        return {}

    cpu_features["cluster_final"] = 0
    total_util_p95 = cpu_features.get(
        "p95_%user", pd.Series(0, index=cpu_features.index)
    ) + cpu_features.get("p95_%system", pd.Series(0, index=cpu_features.index))

    idle_mask = total_util_p95 < idle_threshold
    cpu_features.loc[idle_mask, "cluster_final"] = 99

    busy_mask = total_util_p95 > busy_threshold
    cpu_features.loc[busy_mask, "cluster_final"] = 1

    final_stats = cpu_features.groupby("cluster_final").mean(numeric_only=True).round(2)
    final_counts = cpu_features["cluster_final"].value_counts()
    cluster_label_map = {
        1: "Busy (High Load)",
        0: "Active (Mid)",
        99: "Idle (Background)",
    }

    clusters_summary = []
    for cluster_id in final_stats.index:
        stats = final_stats.loc[cluster_id]
        summary = stats.to_dict()
        cid = int(cluster_id)
        summary["id"] = cid
        summary["Status"] = cluster_label_map.get(cid, f"Unknown ({cid})")
        summary["Count"] = int(final_counts.loc[cluster_id])
        ordered_summary = {"Status": summary["Status"], "Count": summary["Count"]}
        for key, value in summary.items():
            if key not in {"Status", "Count", "id"}:
                ordered_summary[key] = value
        clusters_summary.append(ordered_summary)

    log.info("Analysis complete. Found %s groups.", len(final_stats))

    return {
        "cpu_clusters_summary": clusters_summary,
        "cpu_clusters_count": len(final_stats),
        "cpu_features_df": cpu_features,
        "optimal_eps": 0.20,
    }
