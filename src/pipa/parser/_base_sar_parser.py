from __future__ import annotations

from io import StringIO
from pathlib import Path

import pandas as pd


def _read_file_lines(file_path: Path) -> list[str]:
    with open(file_path, "r", errors="ignore") as file_handle:
        return file_handle.readlines()


def _reconstruct_csv_content(lines: list[str]) -> tuple[str | None, int]:
    header_line_content = None
    data_start_index = 0

    for index, line in enumerate(lines):
        if line.strip().startswith("#"):
            header_line_content = line.strip()[1:].strip()
            data_start_index = index + 1
            break

    return header_line_content, data_start_index


def generic_sar_parse(file_path: Path) -> pd.DataFrame:
    """Parse sar-generated CSV files into a :class:`pandas.DataFrame`.

    The collector emits CSV data whose first non-empty line starts with ``#``.
    The actual header row is encoded after the hash symbol, followed by rows of
    semicolon-separated values. This helper reconstructs the proper CSV content
    before handing it to :func:`pandas.read_csv`.

    Parameters
    ----------
    file_path:
        The CSV file produced by ``sadf -d``.

    Returns
    -------
    pandas.DataFrame
        DataFrame containing the parsed data. Empty if the file is missing or
        0 bytes long.
    """

    if not file_path.exists() or file_path.stat().st_size == 0:
        return pd.DataFrame()

    lines = _read_file_lines(file_path)
    header_line_content, data_start_index = _reconstruct_csv_content(lines)

    if not header_line_content:
        return pd.read_csv(file_path, sep=";")

    csv_content = header_line_content + "\n" + "".join(lines[data_start_index:])
    return pd.read_csv(StringIO(csv_content), sep=";")
