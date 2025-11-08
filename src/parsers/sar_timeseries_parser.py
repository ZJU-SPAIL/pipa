import io
from typing import Any, Dict, List

import pandas as pd

BLOCK_DEFINITIONS = {
    "cpu": {"keywords": ["CPU", "%usr", "%idle"], "primary_key": "CPU"},
    "proc_cswch": {"keywords": ["proc/s", "cswch/s"], "primary_key": "timestamp"},
    "interrupts": {"keywords": ["INTR"], "primary_key": "INTR"},
    "paging": {"keywords": ["pgpgin/s", "pgpgout/s"], "primary_key": "timestamp"},
    "io": {"keywords": ["tps", "rtps", "wtps"], "primary_key": "timestamp"},
    "memory_util": {"keywords": ["kbmemfree", "%memused"], "primary_key": "timestamp"},
    "swap_util": {"keywords": ["kbswpfree", "%swpused"], "primary_key": "timestamp"},
    "load_queue": {"keywords": ["runq-sz", "ldavg-1"], "primary_key": "timestamp"},
    "device_io": {"keywords": ["DEV", "tps", "rkB/s", "wkB/s"], "primary_key": "DEV"},
    "network_dev": {"keywords": ["IFACE", "rxpck/s"], "primary_key": "IFACE"},
    "network_err": {"keywords": ["IFACE", "rxerr/s"], "primary_key": "IFACE"},
    "tcp_stats": {"keywords": ["active/s", "passive/s"], "primary_key": "timestamp"},
}


def _sanitize_header(headers: List[str]) -> List[str]:
    """Cleans up header names to be valid DataFrame column names."""
    return [h.replace("%", "pct_").replace("/s", "_per_s") for h in headers]


def _post_process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Converts timestamp and attempts to convert all other columns to numeric.

    Preserves string columns like 'CPU', 'DEV', 'IFACE' that are identifiers.
    """
    identifier_cols = {"CPU", "DEV", "IFACE", "INTR"}

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], format="%H:%M:%S").dt.time

    for col in df.columns:
        if col not in ["timestamp"] + list(identifier_cols):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        elif col in identifier_cols and col in df.columns:
            df[col] = df[col].astype(str)

    return df


def parse_sar_timeseries(content: str) -> Dict[str, pd.DataFrame]:
    """
    Parses a full `sar -A` output into a dictionary of pandas DataFrames,
    handling multiple, repeating data blocks.

    :param content: The raw string content from the sar -A output file.
    :return: A dictionary where keys are block names (e.g., 'cpu', 'io')
             and values are the corresponding DataFrames.
    """
    all_blocks: Dict[str, List[Dict[str, Any]]] = {name: [] for name in BLOCK_DEFINITIONS}
    current_block_type: str | None = None
    headers: List[str] = []

    file_like_content = io.StringIO(content)

    for line in file_like_content:
        line = line.strip()

        if not line or line.startswith("Linux") or line.startswith("Average:"):
            current_block_type = None
            headers = []
            continue

        is_header = False
        for name, definition in BLOCK_DEFINITIONS.items():
            if all(kw in line for kw in definition["keywords"]):
                current_block_type = name
                parts = line.split()
                if parts and _is_timestamp(parts[0]):
                    parts = parts[1:]
                headers = ["timestamp"] + _sanitize_header(parts)
                is_header = True
                break

        if is_header:
            continue

        if current_block_type and headers:
            values = line.split()
            if values and _is_timestamp(values[0]):
                timestamp = values[0]
                data_values = values[1:]
                if len(data_values) == len(headers) - 1:
                    row_data = {"timestamp": timestamp}
                    row_data.update(dict(zip(headers[1:], data_values)))
                    all_blocks[current_block_type].append(row_data)

    results: Dict[str, pd.DataFrame] = {}
    for block_name, data_list in all_blocks.items():
        if data_list:
            df = pd.DataFrame(data_list)
            results[block_name] = _post_process_dataframe(df)

    return results


def _is_timestamp(s: str) -> bool:
    """Check if a string matches the timestamp format HH:MM:SS."""
    try:
        pd.to_datetime(s, format="%H:%M:%S")
        return True
    except (ValueError, TypeError):
        return False
