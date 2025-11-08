import io
import re

import numpy as np
import pandas as pd


def parse_perf_stat_timeseries(content: str) -> pd.DataFrame:
    """
    Parses complex time-series output of `perf stat -I` into a pandas DataFrame.
    Handles floating point values, percentages, and complex event names.

    :param content: The raw string content from the perf_stat.txt file.
    :return: A DataFrame with columns ['timestamp', 'value', 'unit', 'event_name'].
    """
    data = []

    file_like_content = io.StringIO(content)
    for line in file_like_content:
        line = line.split("#")[0].rstrip()
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        match1 = re.match(
            r"^\s*([\d\.]+)\s+(<not counted>|[\d,]*\.?\d+%?)\s+(.*)$",
            line,
        )

        if not match1:
            continue

        timestamp_str, value_str, rest = match1.groups()

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

        if not unit:
            event_name = rest

        timestamp = float(timestamp_str)

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
                "value": value,
                "unit": unit,
                "event_name": event_name,
            }
        )

    if not data:
        return pd.DataFrame(columns=["timestamp", "value", "unit", "event_name"])

    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_numeric(df["timestamp"])
    df["value"] = pd.to_numeric(df["value"])
    df["unit"] = df["unit"].astype(str)
    df["event_name"] = df["event_name"].astype(str)

    return df
