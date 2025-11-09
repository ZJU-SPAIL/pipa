from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import yaml

from src.engine.analyze import generate_report

MOCK_PERF_DF = pd.DataFrame({"timestamp": [0.1], "cpu": ["all"], "event_name": ["cycles"], "value": [1000]})
MOCK_SAR_DF = pd.DataFrame(
    {
        "timestamp": ["10:00:01"],
        "CPU": ["all"],
        "pct_usr": [10.0],
        "pct_sys": [5.0],
        "pct_idle": [85.0],
    }
)


@pytest.fixture
def sample_test_dir(tmp_path: Path) -> Path:
    """Creates a mock directory structure with necessary files for testing."""
    level_dir = tmp_path / "attach_session"
    level_dir.mkdir()
    (level_dir / "perf_stat.txt").touch()
    (level_dir / "sar_cpu.csv").touch()
    (tmp_path / "static_info.yaml").touch()
    return level_dir


@pytest.mark.parametrize(
    "static_info_exists, sar_exists, perf_exists",
    [
        (True, True, True),
        (False, True, True),
        (True, False, True),
        (True, True, False),
        (True, False, False),
    ],
)
@patch("src.engine.analyze.Environment")
@patch("src.engine.analyze.load_rules", return_value=[])
@patch("pandas.read_csv")
@patch("src.engine.analyze.parse_perf_stat_timeseries")
def test_generate_report_robustness(
    mock_parse_perf,
    mock_read_csv,
    mock_load_rules,
    mock_env,
    sample_test_dir,
    static_info_exists,
    sar_exists,
    perf_exists,
):
    """
    Tests that generate_report handles various combinations of missing files gracefully.
    """
    mock_parse_perf.return_value = MOCK_PERF_DF if perf_exists else pd.DataFrame()
    mock_read_csv.return_value = MOCK_SAR_DF if sar_exists else pd.DataFrame()

    level_dir = sample_test_dir
    static_info_path = level_dir.parent / "static_info.yaml"
    sar_csv_path = level_dir / "sar_cpu.csv"
    perf_txt_path = level_dir / "perf_stat.txt"

    if not static_info_exists and static_info_path.exists():
        static_info_path.unlink()
    if static_info_exists:
        with open(static_info_path, "w") as f:
            yaml.dump({"cpu_info": {"Model_Name": "Test CPU"}}, f)

    if not sar_exists and sar_csv_path.exists():
        sar_csv_path.unlink()

    if not perf_exists and perf_txt_path.exists():
        perf_txt_path.unlink()

    mock_template = MagicMock()
    mock_env.return_value.get_template.return_value = mock_template
    mock_template.render.return_value = "<html></html>"

    generate_report(level_dir, Path("report.html"))

    mock_template.render.assert_called_once()
    call_kwargs = mock_template.render.call_args.kwargs
    warnings = call_kwargs["warnings"]

    if not static_info_exists:
        assert any("static_info.yaml not found" in w for w in warnings)
    if not sar_exists:
        assert any("sar_cpu.csv not found" in w for w in warnings)
    if not perf_exists:
        assert any("perf_stat.txt not found" in w for w in warnings)
