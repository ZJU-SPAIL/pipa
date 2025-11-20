from typing import Dict, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.graph_objects import Figure


def plot_sar_cpu(df: pd.DataFrame) -> Figure:
    """
    Generates an interactive Plotly figure for sar_cpu data.
    """
    if "%user" in df.columns and "%system" in df.columns:
        df["%total"] = df["%user"] + df["%system"]

    metrics_to_plot = [m for m in ["%user", "%system", "%iowait", "%idle", "%total"] if m in df.columns]

    melted_df = df.melt(
        id_vars=["timestamp", "CPU"],
        value_vars=metrics_to_plot,
        var_name="metric",
        value_name="utilization",
    )

    fig = px.line(
        melted_df,
        x="timestamp",
        y="utilization",
        color="CPU",
        line_dash="metric",
        title="Sar CPU Metrics (Per-Core & Overall)",
        labels={"utilization": "CPU Utilization (%)"},
    )

    fig.update_layout(
        height=600,
        showlegend=True,
        legend=dict(
            title="Metrics",
            orientation="v",
            yanchor="top",
            y=1.0,
            xanchor="left",
            x=1.01,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="rgba(0,0,0,0.2)",
            borderwidth=1,
        ),
        margin=dict(r=200),
    )
    return fig


def plot_timeseries_generic(df: pd.DataFrame, name: str) -> Tuple[Dict[str, Figure], Dict[str, Dict]]:
    """
    Generates interactive Plotly figures for any generic time-series DataFrame.
    It intelligently splits metrics into subplots based on their units (KB/s, pages/s, faults/s, %).
    """
    generated_plots: Dict[str, Figure] = {}
    generated_filters: Dict[str, Dict] = {}

    # 定义单位分组规则，基于列名中的关键词
    unit_groups = {
        "rate_per_sec": (["/s", "flt/s"], "Rate (/s)"),
        "kb_per_sec": (["kb/s", "kB/s"], "Throughput (KB/s)"),
        "pages_per_sec": (["pgpgin/s", "pgpgout/s"], "Pages (/s)"),
        "percentage": (["%"], "Percentage (%)"),
        "size_kb": (["kb", "kB"], "Size (KB)"),
        "absolute": ([], "Value"),  # 默认分组
    }

    # 识别DataFrame中的所有数值列
    value_cols_all = [c for c in df.columns if df[c].dtype.kind in "if" and c not in ["interval", "hostname"]]

    # 将数值列分配到不同的单位组
    grouped_cols = {group_name: [] for group_name in unit_groups}

    for col in value_cols_all:
        assigned = False
        for group_name, (keywords, _) in unit_groups.items():
            # 特殊处理 fault/s vs /s 的包含关系
            if group_name == "rate_per_sec" and any(kw in col for kw in ["pgpgin/s", "pgpgout/s"]):
                continue
            if any(kw in col for kw in keywords):
                grouped_cols[group_name].append(col)
                assigned = True
                break
        if not assigned:
            grouped_cols["absolute"].append(col)

    # id_col 用于区分设备或接口，如 'IFACE', 'DEV'
    id_col = next((col for col in ["IFACE", "DEV", "cpu"] if col in df.columns), None)

    # 为每个非空的单位组生成一个图表
    for group_name, cols_to_plot in grouped_cols.items():
        if not cols_to_plot:
            continue

        # 针对 perf 指标的百分比图，使用更专业的标题
        base_title = f"{name.replace('_', ' ').title()} Metrics"
        if name == "perf" and group_name == "percentage":
            base_title = "TMA L1 Metrics"

        plot_name = f"{name}_{group_name}" if len([g for g in grouped_cols.values() if g]) > 1 else name
        chart_title = base_title if plot_name == name else f"{base_title} ({unit_groups[group_name][1]})"
        y_axis_title = unit_groups[group_name][1]

        # Melt data for plotting
        melted_df = df.melt(
            id_vars=["timestamp"] + ([id_col] if id_col else []),
            value_vars=cols_to_plot,
            var_name="metric",
            value_name="value",
        )
        if melted_df.empty:
            continue

        fig = px.line(
            melted_df,
            x="timestamp",
            y="value",
            color="metric",
            line_dash=id_col,
            title=chart_title,
            labels={"value": y_axis_title},
        )
        fig.update_layout(
            height=500,
            showlegend=True,
            legend=dict(
                title="Metrics",
                orientation="v",
                yanchor="top",
                y=1.0,
                xanchor="left",
                x=1.01,
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="rgba(0,0,0,0.2)",
                borderwidth=1,
            ),
            margin=dict(r=200),
        )
        generated_plots[plot_name] = fig

        # 生成过滤器
        filter_options = {"METRIC": sorted(cols_to_plot)}
        if id_col:
            filter_options[id_col] = sorted(df[id_col].unique().tolist())

        if filter_options:
            filters_with_hints = {}
            for key, values in filter_options.items():
                source_property = "legendgroup" if (id_col and key == id_col) else "name"
                filters_with_hints[key] = {
                    "values": values,
                    "sample": values[:3],
                    "count": len(values),
                    "source": source_property,
                }
            generated_filters[f"{plot_name}_filters"] = filters_with_hints

    return generated_plots, generated_filters


def plot_cpu_clusters(cpu_features_df: pd.DataFrame, optimal_eps: float) -> Figure:
    """根据聚类结果生成 CPU 核心行为散点图 (V2 - 峰值感知版)。"""
    df_plot = cpu_features_df.copy()
    # === FIX: 将数字 ID 映射为语义化标签 (Issue #3) ===
    cluster_map = {0: "Active (Mid)", 1: "Busy (High Load)", 99: "Idle (Background)"}
    # 使用 map 进行替换，如果找不到 key 则保留原值
    df_plot["cluster_label"] = df_plot["cluster_final"].map(cluster_map).fillna(df_plot["cluster_final"].astype(str))
    # 定义更加符合直觉的颜色映射
    # 1 (Busy) -> 红色
    # 99 (Idle) -> 绿色
    # 0 (Mid) -> 橙色/黄色
    color_map = {
        "Busy (High Load)": "#EF553B",  # Red
        "Idle (Background)": "#00CC96",  # Green
        "Active (Mid)": "#FFA15A",  # Orange
    }
    # ！！注意：这个函数现在依赖于 cpu_features_df 中包含 mean_* 和 p95_* 的列 ！！
    fig = px.scatter(
        df_plot,
        # 核心修复 1: 使用 'mean_%user' 和 'mean_%system' 作为坐标轴
        x="mean_%user",
        y="mean_%system",
        color="cluster_label",
        # === FIX: 强制指定颜色 ===
        color_discrete_map=color_map,
        # 核心修复 2: 在悬停数据中，同时显示 mean 和 p95 的值
        hover_data={
            "CPU ID": df_plot.index,
            "mean_%idle": ":.2f",
            "p95_%idle": ":.2f",
            "mean_%user": ":.2f",
            "p95_%user": ":.2f",
            "mean_%system": ":.2f",
            "p95_%system": ":.2f",
        },
        title="CPU 核心行为聚类 (物理感知分层)",
        labels={
            "cluster_label": "Core Status",  # 图例标题
            "mean_%user": "平均用户态利用率 (%)",
            "mean_%system": "平均内核态利用率 (%)",
        },
    )
    fig.update_layout(height=600)
    return fig


def plot_knee_distance(k_distances: np.ndarray, elbow_x: int, optimal_eps: float, k: int) -> Figure:
    """(V2 使用) 绘制 K-距离图并用垂直线标记肘部。"""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(range(len(k_distances))), y=k_distances, mode="lines", name="K-Distance"))
    if elbow_x is not None:
        fig.add_vline(
            x=elbow_x,
            line_width=2,
            line_dash="dash",
            line_color="red",
            annotation_text=f" Elbow at eps={optimal_eps:.2f}",
            annotation_position="top left",
        )
    fig.update_layout(
        title_text="K-距离图 (DBSCAN eps 自动寻优)",
        xaxis_title="CPU 核心 (按 K-距离排序)",
        yaxis_title=f"到第 {k} 个邻居的距离 (Epsilon)",
    )
    return fig
