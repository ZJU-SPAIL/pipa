"""Parser for ``perf stat -I`` CSV style outputs."""

from __future__ import annotations

import io
import logging
from typing import Dict

import pandas as pd

log = logging.getLogger(__name__)


def parse(content: str) -> Dict[str, pd.DataFrame]:
    """Parse ``perf stat -I`` CSV output into structured DataFrames."""

    events_data = []
    metrics_data = []
    file_like_content = io.StringIO(content)

    for line in file_like_content:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split(";")
        if len(parts) < 2:
            continue

        try:
            timestamp = float(parts[0])
            cpu_col_val = parts[1].strip()
            has_cpu_col = cpu_col_val.startswith("CPU") or cpu_col_val.startswith("S")

            if has_cpu_col:
                cpu = cpu_col_val
                base_idx = 2
            else:
                cpu = "all"
                base_idx = 1

            idx_val = base_idx
            idx_unit = base_idx + 1
            idx_name = base_idx + 2

            if len(parts) > idx_name:
                val_str = parts[idx_val].strip()
                name_str = parts[idx_name].strip()
                unit_str = parts[idx_unit].strip()

                if val_str and name_str and val_str != "<not counted>":
                    try:
                        val = float(val_str.replace(",", ""))
                        known_units = ["Joules", "Watts", "MHz", "GHz", "bytes"]
                        for unit in known_units:
                            if unit_str == unit or name_str.endswith(unit):
                                unit_str = unit
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

            if len(parts) >= 2:
                possible_metric_name = parts[-1].strip()
                possible_metric_val = parts[-2].strip()
                if possible_metric_name and possible_metric_val:
                    is_known_metric = any(
                        token in possible_metric_name
                        for token in ["IPC", "CPI"]
                    )
                    if is_known_metric:
                        try:
                            metric_value = float(possible_metric_val.replace(",", ""))
                            metrics_data.append(
                                {
                                    "timestamp": timestamp,
                                    "cpu": cpu,
                                    "value": metric_value,
                                    "metric_name": possible_metric_name,
                                    "type": "metric",
                                }
                            )
                        except ValueError:
                            pass
        except Exception:  # pragma: no cover - defensive parsing
            continue

    events_df = (
        pd.DataFrame(events_data)
        if events_data
        else pd.DataFrame(
            columns=["timestamp", "cpu", "value", "unit", "event_name", "type"]
        )
    )
    metrics_df = (
        pd.DataFrame(metrics_data)
        if metrics_data
        else pd.DataFrame(columns=["timestamp", "cpu", "value", "metric_name", "type"])
    )

    for dataframe in (events_df, metrics_df):
        if not dataframe.empty:
            dataframe["timestamp"] = pd.to_numeric(dataframe["timestamp"])
            dataframe["value"] = pd.to_numeric(dataframe["value"])
            dataframe["cpu"] = dataframe["cpu"].astype(str)

    return {"events": events_df, "metrics": metrics_df}
