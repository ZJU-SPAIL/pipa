from pathlib import Path

import pandas as pd
import pytest

# 修正：导入新的函数名
from src.engine.analyze import generate_report

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
def sample_test_dir(tmp_path: Path) -> Path:
    """Creates a temporary directory with mock data files."""
    level_dir = tmp_path / "intensity_1"
    level_dir.mkdir()
    (level_dir / "perf_stat.txt").write_text(MOCK_PERF_DATA)
    (level_dir / "sar_cpu.txt").write_text(MOCK_SAR_DATA)
    return level_dir


def test_generate_report_returns_correct_dataframe(sample_test_dir):
    """
    Tests that generate_report correctly parses, aligns, and returns a DataFrame.
    This test focuses on the data processing logic, ignoring the HTML output.
    """
    fake_report_path = sample_test_dir / "fake_report.html"
    result_df = generate_report(sample_test_dir, fake_report_path)

    assert isinstance(result_df, pd.DataFrame)
    assert not result_df.empty
    assert result_df.shape[0] == 2

    assert "pct_usr" in result_df.columns
    assert "cycles" in result_df.columns
    assert "instructions" in result_df.columns

    second_row = result_df.iloc[1]
    assert second_row["pct_usr"] == 12.00
    assert second_row["cycles"] == 1050
