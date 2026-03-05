"""CPU-specific sar CSV parser.

Provides a thin wrapper around :func:`generic_sar_parse` that normalizes the
``CPU`` column, replacing ``-1`` with ``all`` to denote the aggregated view.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ._base_sar_parser import generic_sar_parse


def parse(file_path: Path) -> pd.DataFrame:
    """Parse ``sar_cpu.csv`` files.

    Parameters
    ----------
    file_path:
        Path to the CSV produced by ``sadf -d -- -P ALL``.
    """

    dataframe = generic_sar_parse(file_path)
    if dataframe.empty or "CPU" not in dataframe.columns:
        return dataframe

    dataframe["CPU"] = dataframe["CPU"].astype(str)
    dataframe.loc[dataframe["CPU"] == "-1", "CPU"] = "all"
    return dataframe
