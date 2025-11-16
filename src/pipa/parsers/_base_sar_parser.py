from io import StringIO
from pathlib import Path

import pandas as pd


def generic_sar_parse(file_path: Path) -> pd.DataFrame:
    """
    A robust, generic parser for all sar-generated CSV files.
    This function encapsulates the shared logic for handling header comments
    and semicolon delimiters.
    """
    if not file_path.exists() or file_path.stat().st_size == 0:
        return pd.DataFrame()

    with open(file_path, "r", errors="ignore") as f:
        lines = f.readlines()

    header_line_content = None
    data_start_index = 0

    for i, line in enumerate(lines):
        if line.strip().startswith("#"):
            header_line_content = line.strip()[1:].strip()
            data_start_index = i + 1
            break

    if not header_line_content:
        return pd.read_csv(file_path, sep=";")

    csv_content = header_line_content + "\n" + "".join(lines[data_start_index:])
    return pd.read_csv(StringIO(csv_content), sep=";")
