import io
import pandas as pd
import re
import numpy as np


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
        # Remove inline comments first
        line = line.split("#")[0].rstrip()
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        # Step 1: Extract timestamp and value using a robust pattern
        # This handles: floats, integers (with/without commas), percentages, and
        # <not counted>
        match1 = re.match(
            r"^\s*([\d\.]+)\s+(<not counted>|[\d,]*\.?\d+%?)\s+(.*)$",
            line,
        )

        if not match1:
            continue

        timestamp_str, value_str, rest = match1.groups()

        # Step 2: Parse the remaining part (unit + event_name)
        # Strategy: Check for known units first. If a known unit is found,
        # everything after it is event_name. Otherwise, treat entire rest as
        # event_name.
        rest = rest.strip()
        unit = ""
        event_name = ""

        # List of known units (prioritized, longest first to avoid partial
        # matches)
        known_units = [
            "Joules",
            "Watts",
            "MHz",  # MHz before GHz to match longest first
            "GHz",
            "KHz",
            "Hz",
            "MB",  # MB before bytes to match longest first
            "KB",
            "TB",
            "GB",
            "bytes",
        ]

        # Check if line starts with a known unit
        for u in known_units:
            if rest.startswith(u):
                unit = u
                event_name = rest[len(u) :].strip()
                break

        # If no known unit found, entire rest is event_name
        if not unit:
            event_name = rest

        # Convert values
        timestamp = float(timestamp_str)

        if value_str == "<not counted>":
            value = np.nan
        else:
            # Remove commas and percentage sign, convert to float
            cleaned_value = value_str.replace(",", "").replace("%", "")
            try:
                value = float(cleaned_value)
            except ValueError:
                # Skip malformed lines
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
    # Ensure correct dtypes
    df["timestamp"] = pd.to_numeric(df["timestamp"])
    df["value"] = pd.to_numeric(df["value"])
    df["unit"] = df["unit"].astype(str)
    df["event_name"] = df["event_name"].astype(str)

    return df
