"""Utility helpers shared across analysis and reporting modules."""

from __future__ import annotations

from pathlib import Path
from typing import Union

import pandas as pd


def p95(series_or_frame: Union[pd.Series, pd.DataFrame]) -> Union[float, pd.Series]:
    """Return the 95th percentile for a Series or DataFrame."""

    return series_or_frame.quantile(0.95)


def get_project_root() -> Path:
    """Return the repository root based on the package location."""

    # This file lives under ``src/pipa/utils.py``; the project root is two
    # levels above ``pipa`` (i.e., ``src``'s parent directory).
    return Path(__file__).resolve().parents[2]
