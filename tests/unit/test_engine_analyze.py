from pathlib import Path

import pandas as pd
import pytest

from src.engine.analyze import run_analysis_poc

MOCK_PERF_DATA = """
0.001     1000      cycles
0.001     2000      instructions
1.001     1050      cycles
1.001     2100      instructions
"""

MOCK_SAR_DATA = """
10:00:00        CPU      %usr     %sys    %idle
10:00:01        all     10.00     5.00   85.00
10:00:02        all     12.00     6.00   82.00
"""


@pytest.fixture
def poc_test_dir(tmp_path: Path) -> Path:
    """Creates a temporary directory structure mimicking a sample run."""
    level_dir = tmp_path / "intensity_1"
    level_dir.mkdir()
    (level_dir / "perf_stat.txt").write_text(MOCK_PERF_DATA)
    (level_dir / "sar_cpu.txt").write_text(MOCK_SAR_DATA)
    return level_dir


def test_run_analysis_poc_success(poc_test_dir):
    """
    Tests that run_analysis_poc correctly parses, aligns, and returns a DataFrame.
    """
    result_df = run_analysis_poc(poc_test_dir)

    assert isinstance(result_df, pd.DataFrame)
    assert not result_df.empty
    assert result_df.shape[0] == 2

    assert "pct_usr" in result_df.columns
    assert "cycles" in result_df.columns
    assert "instructions" in result_df.columns

    second_row = result_df.iloc[1]
    assert second_row["pct_usr"] == 12.00
    assert second_row["cycles"] == 1050
