from pathlib import Path

import pandas as pd

from ._base_sar_parser import generic_sar_parse


def parse(file_path: Path) -> pd.DataFrame:
    """Parses sar_cpu.csv and applies CPU-specific transformations."""
    df = generic_sar_parse(file_path)
    if not df.empty and "CPU" in df.columns:
        df["CPU"] = df["CPU"].astype(str)
        df.loc[df["CPU"] == "-1", "CPU"] = "all"
    return df
