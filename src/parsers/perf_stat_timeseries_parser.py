import io
import re

import numpy as np
import pandas as pd


def parse_perf_stat_timeseries(content: str) -> pd.DataFrame:
    """
    Parses complex time-series output of `perf stat -I [-A]` into a pandas DataFrame.
    Handles floating point values, percentages, per-CPU data, and complex event names.

    :param content: The raw string content from the perf_stat.txt file.
    :return: A DataFrame with columns ['timestamp', 'cpu', 'value', 'unit', 'event_name'].
             The 'cpu' column will be 'all' for aggregated data.
    """
    data = []

    line_regex = re.compile(r"^\s*([\d\.]+)\s+(<not counted>|[\d,]*\.?\d+%?)\s+(?:(CPU\d+)\s+)?(.*)$")

    file_like_content = io.StringIO(content)
    for line in file_like_content:
        line = line.split("#")[0].rstrip().strip()
        if not line:
            continue

        match = line_regex.match(line)
        if not match:
            continue

        timestamp_str, value_str, cpu_id, rest = match.groups()

        rest = rest.strip()
        unit = ""
        event_name = ""

        known_units = [
            "Joules",
            "Watts",
            "MHz",
            "GHz",
            "KHz",
            "Hz",
            "MB",
            "KB",
            "TB",
            "GB",
            "bytes",
        ]
        for u in known_units:
            if rest.startswith(u):
                unit = u
                event_name = rest[len(u) :].strip()
                break
        if not event_name and not unit:
            event_name = rest

        timestamp = float(timestamp_str)
        cpu = cpu_id if cpu_id else "all"

        if value_str == "<not counted>":
            value = np.nan
        else:
            cleaned_value = value_str.replace(",", "").replace("%", "")
            try:
                value = float(cleaned_value)
            except ValueError:
                continue

        data.append(
            {
                "timestamp": timestamp,
                "cpu": cpu,
                "value": value,
                "unit": unit,
                "event_name": event_name,
            }
        )

    if not data:
        return pd.DataFrame(columns=["timestamp", "cpu", "value", "unit", "event_name"])

    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_numeric(df["timestamp"])
    df["value"] = pd.to_numeric(df["value"])
    df["unit"] = df["unit"].astype(str)
    df["event_name"] = df["event_name"].astype(str)
    df["cpu"] = df["cpu"].astype(str)

    return df
