from typing import Any, Dict, List, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.graph_objects import Figure
from plotly.subplots import make_subplots


# 1. 自然排序辅助函数
def _natural_sort(items: List[str]) -> List[str]:
    """
    Performs natural sorting on a list of strings.
    Sorts numeric strings numerically (0, 1, 2, 10) instead of lexicographically (0, 1, 10, 2).
    """

    def sort_key(item):
        try:
            return (0, int(item))
        except ValueError:
            return (1, item)

    return sorted(items, key=sort_key)


def _compress_cpu_ranges(items: list[str]) -> list[str]:
    """
    将 ['0', '1', '2', 'all', 'numa_0'] 智能折叠为 ['0-2', 'all', 'numa_0']。
    用于前端展示，使其看起来更整洁。
    """
    ints = []
    others = []
    for x in items:
        if x.isdigit():
            ints.append(int(x))
        else:
            others.append(x)

    # 对非数字项（all, numa...）进行自然排序
    others = _natural_sort(others)

    if not ints:
        return others

    ints.sort()
    ranges = []
    if ints:
        start = ints[0]
        prev = ints[0]
        for x in ints[1:]:
            if x == prev + 1:
                prev = x
            else:
                ranges.append(f"{start}-{prev}" if start != prev else str(start))
                start = x
                prev = x
        ranges.append(f"{start}-{prev}" if start != prev else str(start))

    # 将特殊选项放在最前面，范围放在最后
    # 比如: ['all', 'workload_avg', 'numa_node_0', '0-127']
    return others + ranges


def plot_sar_cpu(df: pd.DataFrame, context: Dict[str, Any]) -> Tuple[Figure, Dict]:
    """
    Generates an interactive Plotly figure for sar_cpu data AND its filter configuration.
    """
    if "%user" in df.columns and "%system" in df.columns:
        df["%total"] = df["%user"] + df["%system"]

    metrics_to_plot = [
        m for m in ["%user", "%system", "%iowait", "%idle", "%total"] if m in df.columns
    ]

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
        render_mode="webgl",
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

    # --- [核心逻辑移入] 构建前端过滤器 ---
    # 1. 获取基础 CPU 列表
    cpu_options = df["CPU"].unique().tolist()

    # 2. [Feature] 注入 NUMA 节点作为虚拟选项
    if context and "numa_cpu_map" in context:
        cpu_options.extend(context["numa_cpu_map"].keys())

    # 3. 使用自然排序
    sorted_cpus = _natural_sort(list(set(cpu_options)))

    # --- [核心修改] 对 CPU 列表进行智能折叠展示 ---
    # values_for_display: 给人类看的 (e.g. "0-127, all")
    # sorted_cpus: 给代码逻辑用的完整列表 (保留，虽然后端逻辑其实不强依赖它了)

    display_cpus = _compress_cpu_ranges(cpu_options)

    filter_options = {"CPU": sorted_cpus, "METRIC": metrics_to_plot}
    filters_with_hints = {}

    for key, values in filter_options.items():
        # 如果是 CPU，使用折叠后的列表用于展示
        display_values = display_cpus if key == "CPU" else values

        filters_with_hints[key] = {
            "values": display_values,
            "sample": values[:3],
            "count": len(values),
            "source": "legendgroup" if key == "CPU" else "name",
        }

    return fig, filters_with_hints


def plot_timeseries_generic(
    df: pd.DataFrame, name: str
) -> Tuple[Dict[str, Figure], Dict[str, Dict]]:
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
        value_cols_all = [
            c
            for c in df.columns
            if df[c].dtype.kind in "if" and c not in ["interval", "hostname"]
        ]

    # --- 2. 智能分组逻辑 (修复 Paging 单位混乱) ---
    # 优先级：越靠前越优先匹配
    unit_groups = {
        "percentage": (["%"], "Percentage (%)"),
        # Paging 修正: pgpgin/s, pgpgout/s 是 KB (Linux sar 手册确认)
        "throughput_kb": (
            ["kb/s", "kB/s", "pgpgin/s", "pgpgout/s", "rxkB/s", "txkB/s"],
            "Throughput (KB/s)",
        ),
        # Paging 修正: pgfree/s, pgscank/s 等是页面数量 (Pages)
        "pages_count": (
            ["pgfree/s", "pgscank/s", "pgscand/s", "pgsteal/s", "vmeff"],
            "Pages (/s)",
        ),
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

        # 拼接单位后缀
        plot_name = (
            f"{name}_{group_name}"
            if len([g for g in grouped_cols.values() if g]) > 1
            else name
        )
        chart_title = (
            base_title
            if plot_name == name
            else f"{base_title} ({unit_groups[group_name][1]})"
        )
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
                source_property = (
                    "legendgroup" if (id_col and key == id_col) else "name"
                )
                filters_with_hints[key] = {
                    "values": values,
                    "sample": values[:3],
                    "count": len(values),
                    "source": source_property,
                }
            generated_filters[f"{plot_name}_filters"] = filters_with_hints

    return generated_plots, generated_filters


def plot_cpu_clusters(
    cpu_features_df: pd.DataFrame, title: str = "CPU 核心行为分类"
) -> Figure:
    df_plot = cpu_features_df.copy()
    # === FIX: 将数字 ID 映射为语义化标签 (Issue #3) ===
    cluster_map = {0: "Active (Mid)", 1: "Busy (High Load)", 99: "Idle (Background)"}
    # 使用 map 进行替换，如果找不到 key 则保留原值
    df_plot["cluster_label"] = (
        df_plot["cluster_final"]
        .map(cluster_map)
        .fillna(df_plot["cluster_final"].astype(str))
    )
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
        title=title,
        labels={
            "cluster_label": "Core Status",  # 图例标题
            "mean_%user": "平均用户态利用率 (%)",
            "mean_%system": "平均内核态利用率 (%)",
        },
    )
    fig.update_layout(height=600)
    return fig


# === Shared Helpers ===


def _fmt_bytes(size_bytes: float) -> str:
    """简单的人类可读格式化 (GB/TB)"""
    if size_bytes >= 1024**4:
        return f"{size_bytes / (1024**4):.2f} TB"
    elif size_bytes >= 1024**3:
        return f"{size_bytes / (1024**3):.2f} GB"
    elif size_bytes >= 1024**2:
        return f"{size_bytes / (1024**2):.2f} MB"
    return f"{size_bytes} B"


def _get_fs_text(item_info: dict) -> str:
    """生成 Label 上的 Usage 文本"""
    if "fs_usage" in item_info:
        u = item_info["fs_usage"]
        pct = u["percent"]
        color_style = "color:red;" if pct > 90 else ""
        return f"<br><span style='{color_style}'>Used: {pct}%</span>"
    return ""


def _get_fs_hover(item_info: dict) -> str:
    """生成 Hover 上的详细文本"""
    if "fs_usage" in item_info:
        u = item_info["fs_usage"]
        return f"<br>Used: {u['percent']}%<br>Mount: {u['mount']}"
    return ""


# === Chart Generators ===


def plot_disk_sunburst(disk_info: Dict[str, Any]) -> Figure:
    """
    生成全局磁盘旭日图 (Left Side)。
    特性：
    1. 无论是否分区，物理磁盘始终在内环，点击可放大。
    2. 显示使用率警告。
    """
    if not disk_info or "block_devices" not in disk_info:
        return go.Figure()

    ids, labels, parents, values, hover_texts, colors = [], [], [], [], [], []

    # 1. 根节点
    root_id = "Total Storage"
    ids.append(root_id)
    labels.append("Total<br>Storage")  # 稍后更新大小
    parents.append("")
    values.append(0)
    hover_texts.append("All Disks")
    colors.append("#dddddd")

    devices = disk_info.get("block_devices", [])
    total_size = 0

    for disk in devices:
        disk_name = disk.get("name")
        if disk_name.startswith(("loop", "ram")):
            continue
        disk_size = disk.get("size_bytes", 0)
        if disk_size == 0:
            continue

        total_size += disk_size
        rotational = disk.get("rotational", "N/A")

        # --- 构建物理磁盘节点 (Inner Ring) ---
        disk_node_id = f"disk_{disk_name}"
        ids.append(disk_node_id)
        parents.append(root_id)
        values.append(disk_size)

        readable_size = _fmt_bytes(disk_size)
        usage_label = _get_fs_text(disk)  # 如果是 Whole Disk 直接挂载

        # Label: sda (HDD)
        labels.append(
            f"{disk_name}<br><sub>{rotational}</sub><br><b>{readable_size}</b>{usage_label}"
        )

        # Hover
        disk_desc = (
            f"<b>Disk: {disk_name}</b><br>Model: {disk.get('model', 'N/A')}<br>"
            f"Size: {readable_size}{_get_fs_hover(disk)}"
        )
        hover_texts.append(disk_desc)

        # Color
        if rotational == "SSD":
            colors.append("#2ca02c")
        elif rotational == "HDD":
            colors.append("#1f77b4")
        else:
            colors.append("#9467bd")

        # --- 构建子节点 (Outer Ring) ---
        partitions = disk.get("partitions", [])

        # 关键逻辑：如果没有分区，我们必须手动创建一个“虚拟子节点”
        # 这样 `disk_node` 就变成了父节点，点击它可以 Zoom In。
        if not partitions:
            # Virtual Child for Whole Disk
            v_id = f"v_part_{disk_name}"
            ids.append(v_id)
            parents.append(disk_node_id)
            values.append(disk_size)
            labels.append(
                f"Primary<br>Volume<br><b>{readable_size}</b>"
            )  # 显示在 Zoom 后的视图里
            hover_texts.append("Whole Disk Volume")
            colors.append(colors[-1])  # 继承颜色
        else:
            # Normal Partitions
            for part in partitions:
                part_name = part.get("name")
                part_size = part.get("size_bytes", 0)

                ids.append(f"part_{part_name}")
                parents.append(disk_node_id)
                values.append(part_size)

                p_read_size = _fmt_bytes(part_size)
                p_usage = _get_fs_text(part)

                labels.append(f"{part_name}<br><b>{p_read_size}</b>{p_usage}")
                hover_texts.append(
                    f"Partition: {part_name}<br>Size: {p_read_size}{_get_fs_hover(part)}"
                )
                colors.append(colors[-1])  # 继承颜色

    # 更新根节点大小
    values[0] = total_size
    labels[0] = f"Total<br>Storage<br><b>{_fmt_bytes(total_size)}</b>"

    fig = go.Figure(
        go.Sunburst(
            ids=ids,
            labels=labels,
            parents=parents,
            values=values,
            branchvalues="total",
            hovertext=hover_texts,
            hoverinfo="text",
            marker=dict(colors=colors),
            insidetextorientation="radial",
            textinfo="label",
        )
    )
    fig.update_layout(
        margin=dict(t=0, l=0, r=0, b=0), height=500, template="plotly_white"
    )
    return fig


def plot_per_disk_pies(disk_info: Dict[str, Any]) -> Figure:
    """
    生成单盘详情图 (Right Side)。
    【升级】将 Pie Chart 升级为独立的 Sunburst Subplots。
    这样无论分区多小，交互体验和视觉风格都与左侧大图保持一致。
    """
    if not disk_info or "block_devices" not in disk_info:
        return go.Figure()

    # 筛选目标
    targets = []
    for disk in disk_info.get("block_devices", []):
        if disk.get("name", "").startswith(("loop", "ram")):
            continue
        if disk.get("size_bytes", 0) > 0:
            targets.append(disk)

    if not targets:
        return go.Figure()

    # 布局计算
    cols = 3
    rows = (len(targets) + cols - 1) // cols
    titles = [f"{d['name']} ({d.get('rotational', 'N/A')})" for d in targets]

    fig = make_subplots(
        rows=rows,
        cols=cols,
        subplot_titles=titles,
        specs=[[{"type": "domain"}] * cols] * rows,
        vertical_spacing=0.15,
        horizontal_spacing=0.05,
    )

    for idx, disk in enumerate(targets):
        row = (idx // cols) + 1
        col = (idx % cols) + 1

        disk_name = disk.get("name")
        disk_size = disk.get("size_bytes", 0)
        rotational = disk.get("rotational", "N/A")

        # --- 构建 Mini Sunburst 数据 ---
        # 结构: Disk (Root) -> Partitions (Leaves)
        ids, labels, parents, values, hovers, colors = [], [], [], [], [], []

        # 1. Root Node (The Disk itself)
        root_id = disk_name
        ids.append(root_id)
        parents.append("")
        values.append(disk_size)

        readable_total = _fmt_bytes(disk_size)
        labels.append(f"{disk_name}<br>{readable_total}")  # 中心显示总大小
        hovers.append(f"Device: {disk_name}<br>Total: {readable_total}")

        # Base Color
        base_color = "#1f77b4"
        if rotational == "SSD":
            base_color = "#2ca02c"
        elif disk.get("type") == "lvm/dm":
            base_color = "#9467bd"
        colors.append(base_color)

        # 2. Children (Partitions)
        partitions = disk.get("partitions", [])

        if not partitions:
            # Case A: Whole Disk (无分区) -> 添加一个满圆的子节点
            # 这样看起来像一个完整的圆，且鼠标放上去有反应
            ids.append(f"{disk_name}_vol")
            parents.append(root_id)
            values.append(disk_size)

            usage_txt = _get_fs_text(disk)
            labels.append(f"Primary Volume{usage_txt}")
            hovers.append(f"Volume: {disk_name}{_get_fs_hover(disk)}")
            colors.append(base_color)  # 同色
        else:
            # Case B: Partitioned
            used_size = 0
            for part in partitions:
                p_size = part.get("size_bytes", 0)
                used_size += p_size

                ids.append(f"{disk_name}_{part['name']}")
                parents.append(root_id)
                values.append(p_size)

                p_read = _fmt_bytes(p_size)
                p_use = _get_fs_text(part)

                labels.append(f"{part['name']}<br>{p_read}{p_use}")
                hovers.append(
                    f"Partition: {part['name']}<br>Size: {p_read}{_get_fs_hover(part)}"
                )
                colors.append(base_color)

            # Case C: Unallocated Space (Visual Aid)
            free = disk_size - used_size
            if free > 0 and (free / disk_size > 0.01):
                ids.append(f"{disk_name}_free")
                parents.append(root_id)
                values.append(free)
                labels.append(f"Unallocated<br>{_fmt_bytes(free)}")
                hovers.append("Unpartitioned Space")
                colors.append("#dddddd")  # 灰色表示空闲

        # Add Trace
        fig.add_trace(
            go.Sunburst(
                ids=ids,
                labels=labels,
                parents=parents,
                values=values,
                branchvalues="total",
                hovertext=hovers,
                hoverinfo="text",
                marker=dict(colors=colors, line=dict(color="#ffffff", width=1)),
                textinfo="label",
                insidetextorientation="radial",
            ),
            row=row,
            col=col,
        )

    fig.update_layout(
        height=350 * rows, margin=dict(t=30, l=10, r=10, b=10), template="plotly_white"
    )  # 稍微增加高度
    return fig
