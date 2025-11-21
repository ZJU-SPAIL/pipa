from typing import Dict, Tuple

import pandas as pd
import plotly.express as px
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
    Intelligently splits metrics into subplots based on units and scales.
    """
    generated_plots: Dict[str, Figure] = {}
    generated_filters: Dict[str, Dict] = {}

    # --- 1. 数据预处理：内存单位转换 (KB -> GB) ---
    # 需求：内存显示为 GB
    if name == "sar_memory":
        # 找到所有以 kb 开头的列 (如 kbmemfree, kbcached)
        kb_cols = [c for c in df.columns if c.startswith("kb")]
        for col in kb_cols:
            # 转换为 GB (1024 * 1024)
            new_col = col.replace("kb", "") + "_gb"
            df[new_col] = df[col] / (1024 * 1024)

        # 重新定义要画的列，排除原始的 kb 列
        value_cols_all = [c for c in df.columns if c.endswith("_gb") or "%" in c]
    else:
        value_cols_all = [c for c in df.columns if df[c].dtype.kind in "if" and c not in ["interval", "hostname"]]

    # --- 2. 智能分组逻辑 (修复 Paging 单位混乱) ---
    # 优先级：越靠前越优先匹配
    unit_groups = {
        "percentage": (["%"], "Percentage (%)"),
        # Paging 修正: pgpgin/s, pgpgout/s 是 KB (Linux sar 手册确认)
        "throughput_kb": (["kb/s", "kB/s", "pgpgin/s", "pgpgout/s", "rxkB/s", "txkB/s"], "Throughput (KB/s)"),
        # Paging 修正: pgfree/s, pgscank/s 等是页面数量 (Pages)
        "pages_count": (["pgfree/s", "pgscank/s", "pgscand/s", "pgsteal/s", "vmeff"], "Pages (/s)"),
        # Paging 修正: fault/s, majflt/s 是计数 (Count)
        "rate_per_sec": (["/s", "fault/s", "majflt/s", "cswch/s"], "Rate (/s)"),
        # 内存修正: GB 单位
        "size_gb": (["_gb"], "Size (GB)"),
        "size_kb": (["kb", "kB"], "Size (KB)"),  # 兜底
        "absolute": ([], "Value"),
    }

    grouped_cols = {group_name: [] for group_name in unit_groups}

    for col in value_cols_all:
        assigned = False
        for group_name, (keywords, _) in unit_groups.items():
            # 必须完全匹配关键字逻辑，避免 /s 匹配到 kb/s
            # 这里做一个特殊处理：如果 group 是 rate_per_sec (通配 /s)，但列名已经被前面的 throughput_kb (kb/s) 匹配过了，
            # 由于字典顺序，我们需要确保更具体的规则在前。
            # 上面的 unit_groups 顺序已经调整：throughput_kb 在 rate_per_sec 之前。

            if any(kw in col for kw in keywords):
                grouped_cols[group_name].append(col)
                assigned = True
                break
        if not assigned:
            grouped_cols["absolute"].append(col)

    id_col = next((col for col in ["IFACE", "DEV", "cpu"] if col in df.columns), None)

    # --- 3. 绘图循环 ---
    for group_name, cols_to_plot in grouped_cols.items():
        if not cols_to_plot:
            continue

        # 标题修正
        base_title = f"{name.replace('_', ' ').title()} Metrics"

        # 需求: Perf Metrics(Percentages)标题改成TMA信息
        if name == "perf" and group_name == "percentage":
            base_title = "TMA L1 Metrics"

        # 拼接单位后缀
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
