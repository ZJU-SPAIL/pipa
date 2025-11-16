"""Tests for src/engine/analyze.py report generation."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import yaml

from src.pipa.commands.analyze import _generate_report


@pytest.fixture
def mock_level_dir(tmp_path: Path) -> Path:
    """Creates a mock directory structure for analysis."""
    level_dir = tmp_path / "attach_session"
    level_dir.mkdir()

    static_info_path = tmp_path / "static_info.yaml"
    static_info_data = {"cpu_info": {"model_name": "Test CPU", "num_cpu": 8}, "os_info": {"kernel": "5.15.0"}}
    with open(static_info_path, "w") as f:
        yaml.dump(static_info_data, f)

    return level_dir


@pytest.fixture
def mock_perf_data():
    """Mock perf stat data."""
    return pd.DataFrame(
        {
            "timestamp": [1.0, 2.0, 1.0, 2.0],
            "cpu": ["0", "0", "1", "1"],
            "event_name": ["cycles", "cycles", "instructions", "instructions"],
            "value": [1000000, 2000000, 500000, 600000],
        }
    )


@pytest.fixture
def mock_sar_data():
    """Mock SAR CPU data with original column names."""
    return pd.DataFrame(
        {
            "hostname": ["testhost", "testhost"],
            "interval": [1, 1],
            "timestamp": ["13:00:00", "13:00:01"],
            "CPU": ["-1", "-1"],
            "%user": [25.5, 30.2],
            "%system": [10.1, 12.3],
            "%idle": [64.4, 57.5],
        }
    )


@pytest.fixture
def mock_dependencies(mock_perf_data, mock_sar_data):
    """
    This fixture isolates the `_generate_report` function by mocking all its
    external dependencies. It allows us to test the data flow and rendering logic
    of `_generate_report` itself, without actually running the complex sub-functions
    like rule engines or file parsers.

    It yields a dictionary of mocks that tests can use for assertions.
    """
    mock_parser_registry = {
        "perf_stat": MagicMock(return_value=mock_perf_data),
        "sar_cpu": MagicMock(return_value=mock_sar_data),
    }

    mock_load_rules = MagicMock(return_value=([], {}))
    mock_calculate_context = MagicMock(return_value={"num_cpu": 8})
    mock_format_tree = MagicMock(return_value=("<tree>", "<findings>"))

    mock_template = MagicMock()
    mock_template.render.return_value = "<html>Mocked Report</html>"
    mock_environment = MagicMock()
    mock_environment.get_template.return_value = mock_template

    with (
        patch("src.pipa.commands.analyze.PARSER_REGISTRY", new=mock_parser_registry),
        patch("src.pipa.commands.analyze.load_rules", new=mock_load_rules),
        patch("src.pipa.commands.analyze.build_full_context", new=mock_calculate_context),
        patch("src.pipa.commands.analyze.format_rules_to_html_tree", new=mock_format_tree),
        patch("src.pipa.report.html_generator.Environment", return_value=mock_environment),
    ):
        yield {
            "template": mock_template,
            "build_full_context": mock_calculate_context,
        }


def test_generate_report_with_all_data(mock_level_dir, mock_dependencies, tmp_path):
    """Test report generation when all data files exist."""
    (mock_level_dir / "perf_stat.txt").write_text("1.000000000;0;cycles;1000000")

    sar_content = "#hostname;interval;timestamp;CPU;%user;%system;%idle\n"
    sar_content += "testhost;1;13:00:00;-1;25.5;10.1;64.4\n"
    (mock_level_dir / "sar_cpu.csv").write_text(sar_content)

    (mock_level_dir / "perf.data").write_text("")

    report_path = tmp_path / "report.html"

    result = _generate_report(mock_level_dir, report_path)

    assert result is None
    mock_dependencies["template"].render.assert_called()
    call_kwargs = mock_dependencies["template"].render.call_args.kwargs

    assert "warnings" in call_kwargs
    assert "plots" in call_kwargs
    assert "tables_json" in call_kwargs
    assert "findings_for_tree_html" in call_kwargs
    assert "static_info_str" in call_kwargs

    assert len(call_kwargs["warnings"]) == 0


def test_generate_report_missing_perf_data(mock_level_dir, mock_dependencies, tmp_path):
    """Test report generation when perf_stat.txt is missing."""
    sar_content = "#hostname;interval;timestamp;CPU;%user;%system;%idle\n"
    sar_content += "testhost;1;13:00:00;-1;25.5;10.1;64.4\n"
    (mock_level_dir / "sar_cpu.csv").write_text(sar_content)

    report_path = tmp_path / "report.html"

    _generate_report(mock_level_dir, report_path)

    call_kwargs = mock_dependencies["template"].render.call_args.kwargs
    warnings = call_kwargs["warnings"]

    assert any("perf_stat.txt not found" in w for w in warnings)
    assert "plots" in call_kwargs


def test_generate_report_missing_perf_data_file(mock_level_dir, mock_dependencies, tmp_path):
    """Test report generation when perf.data is missing."""
    (mock_level_dir / "perf_stat.txt").write_text("1.000000000;0;cycles;1000000")

    sar_content = "#hostname;interval;timestamp;CPU;%user;%system;%idle\n"
    sar_content += "testhost;1;13:00:00;-1;25.5;10.1;64.4\n"
    (mock_level_dir / "sar_cpu.csv").write_text(sar_content)

    report_path = tmp_path / "report.html"

    _generate_report(mock_level_dir, report_path)

    call_kwargs = mock_dependencies["template"].render.call_args.kwargs
    warnings = call_kwargs["warnings"]

    assert any("perf.data not found" in w for w in warnings)


def test_generate_report_missing_sar_data(mock_level_dir, mock_dependencies, tmp_path):
    """Test report generation when sar_*.csv files are missing."""
    (mock_level_dir / "perf_stat.txt").write_text("1.0;0;cycles;1000")
    report_path = tmp_path / "report.html"

    _generate_report(mock_level_dir, report_path)

    call_kwargs = mock_dependencies["template"].render.call_args.kwargs

    assert "plots" in call_kwargs
    assert "sar_cpu" not in call_kwargs["plots"]


def test_generate_report_missing_static_info(mock_level_dir, mock_dependencies, tmp_path):
    """Test report generation when static_info.yaml is missing."""
    (mock_level_dir.parent / "static_info.yaml").unlink()

    (mock_level_dir / "perf_stat.txt").write_text("1.000000000;0;cycles;1000000")
    sar_content = "#hostname;interval;timestamp;CPU;%user;%system;%idle\n"
    sar_content += "testhost;1;13:00:00;-1;25.5;10.1;64.4\n"
    (mock_level_dir / "sar_cpu.csv").write_text(sar_content)

    report_path = tmp_path / "report.html"

    _generate_report(mock_level_dir, report_path)

    call_kwargs = mock_dependencies["template"].render.call_args.kwargs
    warnings = call_kwargs["warnings"]

    assert any("static_info.yaml not found" in w for w in warnings)
    assert call_kwargs["static_info_str"] == ""


def test_generate_report_empty_perf_file(mock_level_dir, mock_dependencies, tmp_path):
    """Test report generation when perf_stat.txt is empty."""
    (mock_level_dir / "perf_stat.txt").write_text("")

    sar_content = "#hostname;interval;timestamp;CPU;%user;%system;%idle\n"
    sar_content += "testhost;1;13:00:00;-1;25.5;10.1;64.4\n"
    (mock_level_dir / "sar_cpu.csv").write_text(sar_content)

    report_path = tmp_path / "report.html"

    _generate_report(mock_level_dir, report_path)

    call_kwargs = mock_dependencies["template"].render.call_args.kwargs
    warnings = call_kwargs["warnings"]

    assert any("perf_stat.txt is empty" in w for w in warnings)


def test_generate_report_writes_html_file(mock_level_dir, tmp_path):
    """Test that the report is actually written to disk."""
    (mock_level_dir / "perf_stat.txt").write_text("1.000000000;0;cycles;1000000")

    sar_content = "#hostname;interval;timestamp;CPU;%user;%system;%idle\n"
    sar_content += "testhost;1;13:00:00;-1;25.5;10.1;64.4\n"
    (mock_level_dir / "sar_cpu.csv").write_text(sar_content)

    report_path = tmp_path / "test_report.html"

    with (
        patch(
            "src.pipa.commands.analyze.PARSER_REGISTRY",
            {
                "perf_stat": MagicMock(return_value=pd.DataFrame()),
                "sar_cpu": MagicMock(return_value=pd.DataFrame()),
            },
        ),
        patch("src.pipa.commands.analyze.load_rules", return_value=([], {})),
        patch("src.pipa.commands.analyze.build_full_context", return_value={}),
        patch("src.pipa.commands.analyze.format_rules_to_html_tree", return_value=("", "")),
        patch("src.pipa.report.html_generator.Environment") as mock_env,
    ):
        mock_template = MagicMock()
        mock_template.render.return_value = "<html>Test Report</html>"
        mock_env.return_value.get_template.return_value = mock_template

        _generate_report(mock_level_dir, report_path)

    assert report_path.exists()
    content = report_path.read_text()
    assert "<html>Test Report</html>" in content
