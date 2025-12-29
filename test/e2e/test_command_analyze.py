"""Tests for pipa.commands.analyze report generation."""

import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import yaml

from pipa.commands.analyze import _generate_report, analyze_archive


@pytest.fixture
def mock_level_dir(tmp_path: Path) -> Path:
    """Create a mock directory structure for analysis."""

    level_dir = tmp_path / "attach_session"
    level_dir.mkdir()

    static_info_path = tmp_path / "static_info.yaml"
    static_info_data = {
        "cpu_info": {"model_name": "Test CPU", "num_cpu": 8},
        "os_info": {"kernel": "5.15.0"},
    }
    with open(static_info_path, "w", encoding="utf-8") as file_obj:
        yaml.dump(static_info_data, file_obj)

    return level_dir


@pytest.fixture
def mock_perf_data():
    """Mock perf stat data."""

    return pd.DataFrame(
        {
            "timestamp": [1.0, 2.0, 1.0, 2.0],
            "cpu": ["0", "0", "1", "1"],
            "event_name": ["cycles", "cycles", "instructions", "instructions"],
            "value": [1_000_000, 2_000_000, 500_000, 600_000],
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
    """Mock external dependencies used by _generate_report."""

    mock_parser_registry = {
        "perf_stat": MagicMock(return_value=mock_perf_data),
        "sar_cpu": MagicMock(return_value=mock_sar_data),
    }

    mock_load_rules = MagicMock(return_value=([], {}))
    mock_calculate_context = MagicMock(return_value={"num_cpu": 8})
    mock_format_tree = MagicMock(return_value=("<audit>", "<tree>", "<findings>"))

    mock_template = MagicMock()
    mock_template.render.return_value = "<html>Mocked Report</html>"
    mock_environment = MagicMock()
    mock_environment.get_template.return_value = mock_template

    with (
        patch("pipa.commands.analyze.PARSER_REGISTRY", new=mock_parser_registry),
        patch("pipa.commands.analyze.load_rules", new=mock_load_rules),
        patch("pipa.commands.analyze.build_full_context", new=mock_calculate_context),
        patch("pipa.commands.analyze.format_rules_to_html_tree", new=mock_format_tree),
        patch("pipa.report.html_generator.Environment", return_value=mock_environment),
    ):
        yield {
            "template": mock_template,
            "build_full_context": mock_calculate_context,
        }


def test_generate_report_with_all_data(mock_level_dir, mock_dependencies, tmp_path):
    """Test report generation when all data files exist."""

    (mock_level_dir / "perf_stat.txt").write_text(
        "1.000000000;0;cycles;1000000", encoding="utf-8"
    )
    sar_content = "#hostname;interval;timestamp;CPU;%user;%system;%idle\n"
    sar_content += "testhost;1;13:00:00;-1;25.5;10.1;64.4\n"
    (mock_level_dir / "sar_cpu.csv").write_text(sar_content, encoding="utf-8")
    (mock_level_dir / "perf.data").write_text("", encoding="utf-8")

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
    (mock_level_dir / "sar_cpu.csv").write_text(sar_content, encoding="utf-8")

    report_path = tmp_path / "report.html"

    _generate_report(mock_level_dir, report_path)

    call_kwargs = mock_dependencies["template"].render.call_args.kwargs
    warnings = call_kwargs["warnings"]

    assert any("perf_stat.txt not found" in warning for warning in warnings)
    assert "plots" in call_kwargs


def test_generate_report_missing_perf_data_file(
    mock_level_dir, mock_dependencies, tmp_path
):
    """Test report generation when perf.data is missing."""

    (mock_level_dir / "perf_stat.txt").write_text(
        "1.000000000;0;cycles;1000000", encoding="utf-8"
    )
    sar_content = "#hostname;interval;timestamp;CPU;%user;%system;%idle\n"
    sar_content += "testhost;1;13:00:00;-1;25.5;10.1;64.4\n"
    (mock_level_dir / "sar_cpu.csv").write_text(sar_content, encoding="utf-8")

    report_path = tmp_path / "report.html"

    _generate_report(mock_level_dir, report_path)

    call_kwargs = mock_dependencies["template"].render.call_args.kwargs
    warnings = call_kwargs["warnings"]

    assert any("perf.data not found" in warning for warning in warnings)


def test_generate_report_missing_sar_data(mock_level_dir, mock_dependencies, tmp_path):
    """Test report generation when sar_*.csv files are missing."""

    (mock_level_dir / "perf_stat.txt").write_text("1.0;0;cycles;1000", encoding="utf-8")
    report_path = tmp_path / "report.html"

    _generate_report(mock_level_dir, report_path)

    call_kwargs = mock_dependencies["template"].render.call_args.kwargs

    assert "plots" in call_kwargs
    assert "sar_cpu" not in call_kwargs["plots"]


def test_generate_report_missing_static_info(
    mock_level_dir, mock_dependencies, tmp_path
):
    """Test report generation when static_info.yaml is missing."""

    (mock_level_dir.parent / "static_info.yaml").unlink()

    (mock_level_dir / "perf_stat.txt").write_text(
        "1.000000000;0;cycles;1000000", encoding="utf-8"
    )
    sar_content = "#hostname;interval;timestamp;CPU;%user;%system;%idle\n"
    sar_content += "testhost;1;13:00:00;-1;25.5;10.1;64.4\n"
    (mock_level_dir / "sar_cpu.csv").write_text(sar_content, encoding="utf-8")

    report_path = tmp_path / "report.html"

    _generate_report(mock_level_dir, report_path)

    call_kwargs = mock_dependencies["template"].render.call_args.kwargs
    warnings = call_kwargs["warnings"]

    assert any("static_info.yaml not found" in warning for warning in warnings)
    assert call_kwargs["static_info_str"] == ""


def test_generate_report_empty_perf_file(mock_level_dir, mock_dependencies, tmp_path):
    """Test report generation when perf_stat.txt is empty."""

    (mock_level_dir / "perf_stat.txt").write_text("", encoding="utf-8")
    sar_content = "#hostname;interval;timestamp;CPU;%user;%system;%idle\n"
    sar_content += "testhost;1;13:00:00;-1;25.5;10.1;64.4\n"
    (mock_level_dir / "sar_cpu.csv").write_text(sar_content, encoding="utf-8")

    report_path = tmp_path / "report.html"

    _generate_report(mock_level_dir, report_path)

    call_kwargs = mock_dependencies["template"].render.call_args.kwargs
    warnings = call_kwargs["warnings"]

    assert any("perf_stat.txt is empty" in warning for warning in warnings)


def test_generate_report_writes_html_file(mock_level_dir, tmp_path):
    """Test that the report is actually written to disk."""

    (mock_level_dir / "perf_stat.txt").write_text(
        "1.000000000;0;cycles;1000000", encoding="utf-8"
    )
    sar_content = "#hostname;interval;timestamp;CPU;%user;%system;%idle\n"
    sar_content += "testhost;1;13:00:00;-1;25.5;10.1;64.4\n"
    (mock_level_dir / "sar_cpu.csv").write_text(sar_content, encoding="utf-8")

    report_path = tmp_path / "test_report.html"

    with (
        patch(
            "pipa.commands.analyze.PARSER_REGISTRY",
            {
                "perf_stat": MagicMock(return_value=pd.DataFrame()),
                "sar_cpu": MagicMock(return_value=pd.DataFrame()),
            },
        ),
        patch("pipa.commands.analyze.load_rules", return_value=([], {})),
        patch("pipa.commands.analyze.build_full_context", return_value={}),
        patch(
            "pipa.commands.analyze.format_rules_to_html_tree", return_value=("", "", "")
        ),
        patch("pipa.report.html_generator.Environment") as mock_env,
    ):
        mock_template = MagicMock()
        mock_template.render.return_value = "<html>Test Report</html>"
        mock_env.return_value.get_template.return_value = mock_template

        _generate_report(mock_level_dir, report_path)

    assert report_path.exists()
    assert "<html>Test Report</html>" in report_path.read_text(encoding="utf-8")


def _write_sar_csv(file_path: Path, header: list[str], rows: list[list[str]]) -> None:
    lines = ["#" + ";".join(header)]
    lines.extend(";".join(map(str, row)) for row in rows)
    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_perf_stat_sample(file_path: Path) -> None:
    lines = [
        "1.000;CPU0;1000000;;cycles",
        "1.000;CPU0;250000;;instructions;0.85;frontend_bound",
    ]
    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_analyze_archive_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Run the full analyze_archive flow against a synthetic collection."""

    bundle_dir = tmp_path / "bundle"
    attach_dir = bundle_dir / "attach_session_demo"
    attach_dir.mkdir(parents=True, exist_ok=True)

    static_info = {
        "cpu_info": {"CPU(s)": 2, "Model name": "Demo CPU"},
        "disk_info": {
            "block_devices": [
                {
                    "name": "sda",
                    "rotational": "SSD",
                    "fs_usage": {"percent": 92, "mount": "/", "total": 10, "used": 9, "free": 1},
                    "partitions": [],
                }
            ]
        },
    }
    static_info_path = bundle_dir / "static_info.yaml"
    static_info_path.write_text(yaml.dump(static_info, allow_unicode=True), encoding="utf-8")

    _write_perf_stat_sample(attach_dir / "perf_stat.txt")
    _write_sar_csv(
        attach_dir / "sar_cpu.csv",
        ["hostname", "interval", "timestamp", "CPU", "%user", "%system", "%iowait", "%idle"],
        [
            ["testhost", 1, "00:00:01", "-1", 35.0, 20.0, 5.0, 40.0],
            ["testhost", 1, "00:00:01", "0", 55.0, 25.0, 10.0, 10.0],
            ["testhost", 1, "00:00:01", "1", 15.0, 5.0, 2.0, 78.0],
        ],
    )
    _write_sar_csv(
        attach_dir / "sar_io.csv",
        ["hostname", "interval", "timestamp", "tps", "rkB/s", "wkB/s", "await", "%util", "avgrq-sz", "avgqu-sz"],
        [["testhost", 1, "00:00:01", 120.0, 400.0, 600.0, 8.0, 81.0, 18.0, 1.2]],
    )
    _write_sar_csv(
        attach_dir / "sar_disk.csv",
        ["hostname", "interval", "timestamp", "DEV", "tps", "rkB/s", "wkB/s", "avgrq-sz", "avgqu-sz", "await", "%util"],
        [["testhost", 1, "00:00:01", "sda", 100.0, 500.0, 700.0, 16.0, 0.8, 9.0, 88.0]],
    )
    _write_sar_csv(
        attach_dir / "sar_network.csv",
        ["hostname", "interval", "timestamp", "IFACE", "%ifutil", "rxkB/s", "txkB/s"],
        [["testhost", 1, "00:00:01", "ens0", 35.0, 128.0, 64.0]],
    )
    _write_sar_csv(
        attach_dir / "sar_memory.csv",
        ["hostname", "interval", "timestamp", "kbmemfree", "kbmemused", "%memused", "%commit"],
        [["testhost", 1, "00:00:01", 1024_000, 512_000, 33.0, 12.0]],
    )
    _write_sar_csv(
        attach_dir / "sar_paging.csv",
        ["hostname", "interval", "timestamp", "pgpgin/s", "pgpgout/s", "majflt/s", "pswpin/s", "pswpout/s"],
        [["testhost", 1, "00:00:01", 10.0, 5.0, 0.5, 0.0, 0.0]],
    )
    _write_sar_csv(
        attach_dir / "sar_load.csv",
        ["hostname", "interval", "timestamp", "runq-sz", "plist-sz", "ldavg-1", "ldavg-5", "ldavg-15"],
        [["testhost", 1, "00:00:01", 1, 100, 2.5, 2.0, 1.5]],
    )

    (attach_dir / "perf.data").write_bytes(b"PERF")

    monkeypatch.setattr(
        "pipa.commands.analyze.extract_hotspots",
        lambda *_, **__: [
            {
                "Overhead": 12.3,
                "Samples": 8,
                "Process": "demo",
                "Library": "demo.so",
                "Symbol": "demo_fn",
                "Scope": "User",
            }
        ],
    )

    archive_path = tmp_path / "pipa-collection-demo.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(attach_dir, arcname="attach_session_demo")
        tar.add(static_info_path, arcname="static_info.yaml")

    report_path = tmp_path / "analysis_report.html"
    analyze_archive(
        str(archive_path),
        output_path=str(report_path),
        expected_cpus="0-1",
    )

    html_output = report_path.read_text(encoding="utf-8")
    assert "PIPA Analysis Report" in html_output
    assert "Sar CPU Metrics" in html_output
    assert "demo_fn" in html_output
    assert "Capacity Warnings" in html_output
