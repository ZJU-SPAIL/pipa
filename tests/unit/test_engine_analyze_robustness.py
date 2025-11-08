from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import yaml

from src.engine.analyze import generate_report

# 为了测试的独立性，我们使用最精简的 mock 数据
MOCK_PERF_DATA = "0.001     1000      cycles\n1.001     1050      cycles\n"
MOCK_SAR_DATA = "10:00:01  all 10.00 5.00 85.00\n10:00:02 all 12.00 6.00 82.00\n"


@pytest.fixture
def sample_test_dir(tmp_path: Path) -> Path:
    level_dir = tmp_path / "intensity_1"
    level_dir.mkdir()
    (level_dir / "perf_stat.txt").touch()
    (level_dir / "sar_cpu.txt").touch()
    (tmp_path / "static_info.yaml").touch()
    return level_dir


# 我们将两个测试场景合并为一个更强大的测试函数
@pytest.mark.parametrize(
    "static_info_exists, static_info_data",
    [
        (True, {"cpu_info": {"Model_Name": "Test CPU"}}),  # 场景1: static_info 存在
        (False, None),  # 场景2: static_info 不存在
    ],
)
@patch("src.engine.analyze.Environment")
@patch("src.engine.analyze.load_rules", return_value=[])
@patch("src.engine.analyze.parse_sar_timeseries")
@patch("src.engine.analyze.parse_perf_stat_timeseries")
def test_generate_report_handles_static_info(
    mock_parse_perf, mock_parse_sar, mock_load_rules, mock_env, sample_test_dir, static_info_exists, static_info_data
):
    """
    一个统一的测试，验证 generate_report 在 static_info.yaml 存在与否两种情况下的行为。
    """
    mock_parse_perf.return_value = pd.DataFrame({"timestamp": [0.1], "event_name": ["cycles"], "value": [1000]})
    mock_parse_sar.return_value = {
        "cpu": pd.DataFrame({"timestamp": ["10:00:01"], "CPU": ["all"], "pct_usr": [10.0], "pct_sys": [5.0]})
    }

    static_info_path = sample_test_dir.parent / "static_info.yaml"
    if static_info_exists:
        with open(static_info_path, "w") as f:
            yaml.dump(static_info_data, f)
    else:
        if static_info_path.exists():
            static_info_path.unlink()

    mock_template = MagicMock()
    mock_env.return_value.get_template.return_value = mock_template
    mock_template.render.return_value = "<html></html>"

    generate_report(sample_test_dir, Path("report.html"))

    mock_template.render.assert_called_once()
    call_kwargs = mock_template.render.call_args.kwargs
    assert "static_info_str" in call_kwargs

    if static_info_exists:
        assert "Model_Name: Test CPU" in call_kwargs["static_info_str"]
    else:
        assert call_kwargs["static_info_str"] == ""
