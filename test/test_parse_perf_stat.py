import pytest
from unittest.mock import mock_open, patch
import pandas as pd
from pandas.testing import assert_frame_equal
from io import StringIO
from pipa.parser.perf_stat import PerfStatData


# Fixture for sample data
@pytest.fixture
def sample_data():
    return """
# started on Mon Jul 15 23:53:10 2024

1.001060857,CPU0,45892724,,cycles,1037560862,100.00,,
1.001060857,CPU1,31607000,,cycles,1037631576,100.00,,
1.001060857,CPU2,15936152,,cycles,1037681348,100.00,,
1.001060857,CPU3,7316201,,cycles,1037628759,100.00,,
1.001060857,CPU4,28015727,,cycles,1037603520,100.00,,
1.001060857,CPU5,37519594,,cycles,1037584024,100.00,,
1.001060857,CPU6,346613976,,cycles,1037519925,100.00,,
"""


# Fixture for expected DataFrame
@pytest.fixture
def expected_df():
    return pd.DataFrame(
        {
            "timestamp": [1.001060857] * 7,
            "cpu_id": list(range(7)),
            "value": [
                45892724,
                31607000,
                15936152,
                7316201,
                28015727,
                37519594,
                346613976,
            ],
            "unit": ["nan"] * 7,
            "metric_type": ["cycles"] * 7,
            "run_time(ns)": [
                1037560862,
                1037631576,
                1037681348,
                1037628759,
                1037603520,
                1037584024,
                1037519925,
            ],
            "run_percentage": [
                100.00,
                100.00,
                100.00,
                100.00,
                100.00,
                100.00,
                100.00,
            ],
            "opt_value": [float("nan")] * 7,
            "opt_unit_metric": ["nan"] * 7,
        }
    )


@patch("builtins.open", new_callable=mock_open)
def test_parse_perf_stat_file(mock_file, sample_data, expected_df):
    mock_file.return_value = StringIO(sample_data.strip())

    result_df = PerfStatData.parse_perf_stat_file("dummy_path")

    result_df.replace("", float("nan"), inplace=True)

    # Compare the result with the expected DataFrame
    assert_frame_equal(result_df, expected_df, check_like=True)


if __name__ == "__main__":
    pytest.main([__file__])
