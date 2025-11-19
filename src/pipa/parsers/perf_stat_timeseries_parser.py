# src/pipa/parsers/perf_stat_timeseries_parser.py

import io
import logging

import pandas as pd

log = logging.getLogger(__name__)


def parse(content: str) -> dict:
    """
    将`perf stat -I [-A] -x ";"`的CSV格式时间序列输出解析为结构化数据。
    """
    events_data = []
    metrics_data = []

    file_like_content = io.StringIO(content)
    for line in file_like_content:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split(";")
        # 至少要有时间戳
        if len(parts) < 2:
            continue

        try:
            timestamp = float(parts[0])

            # 1. 确定 CPU 列是否存在
            # 逻辑：如果第二列是 "CPUx" 或 "S0-Cx"，则有 CPU 列
            # 如果第二列是数字或空，则没有
            cpu_col_val = parts[1].strip()
            has_cpu_col = cpu_col_val.startswith("CPU") or cpu_col_val.startswith("S")

            if has_cpu_col:
                cpu = cpu_col_val
                base_idx = 2  # Value 在第 3 列
            else:
                cpu = "all"
                base_idx = 1  # Value 在第 2 列

            # 定义列索引 (基于 base_idx)
            idx_val = base_idx
            idx_unit = base_idx + 1
            idx_name = base_idx + 2

            # === 1. 解析 Event (如果存在) ===
            # 只有当这一行有足够多的列，并且 Value 不为空时，才尝试解析 Event
            if len(parts) > idx_name:
                val_str = parts[idx_val].strip()
                name_str = parts[idx_name].strip()
                unit_str = parts[idx_unit].strip()

                if val_str and name_str and val_str != "<not counted>":
                    try:
                        val = float(val_str.replace(",", ""))

                        # 简单的单位提取逻辑
                        known_units = ["Joules", "Watts", "MHz", "GHz", "bytes"]
                        for u in known_units:
                            if unit_str == u or name_str.endswith(u):
                                unit_str = u
                                break

                        events_data.append(
                            {
                                "timestamp": timestamp,
                                "cpu": cpu,
                                "value": val,
                                "unit": unit_str,
                                "event_name": name_str,
                                "type": "event",
                            }
                        )
                    except ValueError:
                        pass

            # === 2. 解析 Metric (动态定位) ===
            # Metric 总是位于行的最后两列：[... MetricVal; MetricName]
            # 不管中间空了多少列，只要最后两列看起来像 Metric，就抓取

            if len(parts) >= 2:
                possible_metric_name = parts[-1].strip()
                possible_metric_val = parts[-2].strip()

                # 简单的启发式规则：Metric Name 通常包含字母，Metric Val 是数字
                # 且这一行必须是 perf metric 输出（通常包含 retiring, bound 等关键词）
                # 或者我们信任 perf -M 的输出结构

                # 过滤掉显然不是 Metric 的行（比如只有 Event 的行）
                # 典型 Metric 行：...;100.00;0.89;backend_bound
                # 典型 Event 行： ...;cpu_cycles;100.00;;

                # 如果倒数第二列是百分比 (100.00) 或者空，那可能不是 Metric 值
                # Metric 值通常是 0.xx 或者整数

                if possible_metric_name and possible_metric_val:
                    # 检查名字是否像一个 Metric (可选，为了稳健)
                    is_known_metric = any(
                        k in possible_metric_name for k in ["bound", "retiring", "speculation", "IPC", "CPI"]
                    )

                    if is_known_metric:
                        try:
                            m_val = float(possible_metric_val.replace(",", ""))
                            # 转换为百分比: 0.89 -> 89.0
                            # 注意：有些 Metric 可能是 IPC (1.2)，不需要乘 100
                            # 这里我们只针对 TopDown 指标乘 100
                            if (
                                "bound" in possible_metric_name
                                or "retiring" in possible_metric_name
                                or "speculation" in possible_metric_name
                            ):
                                m_val = m_val * 100.0

                            metrics_data.append(
                                {
                                    "timestamp": timestamp,
                                    "cpu": cpu,
                                    "value": m_val,
                                    "metric_name": possible_metric_name,
                                    "type": "metric",
                                }
                            )
                        except ValueError:
                            pass

        except Exception:
            continue

    # 创建DataFrames
    events_df = (
        pd.DataFrame(events_data)
        if events_data
        else pd.DataFrame(columns=["timestamp", "cpu", "value", "unit", "event_name", "type"])
    )
    metrics_df = (
        pd.DataFrame(metrics_data)
        if metrics_data
        else pd.DataFrame(columns=["timestamp", "cpu", "value", "metric_name", "type"])
    )

    # 类型转换
    for df in [events_df, metrics_df]:
        if not df.empty:
            df["timestamp"] = pd.to_numeric(df["timestamp"])
            df["value"] = pd.to_numeric(df["value"])
            df["cpu"] = df["cpu"].astype(str)

    return {"events": events_df, "metrics": metrics_df}
