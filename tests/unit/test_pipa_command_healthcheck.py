import logging
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.pipa.commands.healthcheck import _collect_all_static_info

# --- Mock Data for v2.2 Collectors ---
MOCK_OS_RELEASE_CONTENT = 'NAME="openEuler"\nVERSION="22.03"\nID="openEuler"'
MOCK_CPUINFO_CONTENT = "processor: 0\nprocessor: 1\nmodel name: Test CPU\n"
MOCK_MEMINFO_CONTENT = "MemTotal: 1024 kB\n"
MOCK_SYSCTL_OUTPUT = "vm.swappiness = 60\nfs.file-max = 100000"
MOCK_UNAME_OUTPUT = "5.10.0-test-kernel"
MOCK_IP_ADDR_OUTPUT = "1: lo: <LOOPBACK,UP>\n inet 127.0.0.1/8"


@pytest.fixture(autouse=True)
def setup_logging_for_test(caplog):
    """Set log level to capture warnings for all tests in this module."""
    caplog.set_level(logging.WARNING, logger="src.pipa.commands.healthcheck")


@patch("src.pipa.commands.healthcheck.run_command")
@patch("pathlib.Path.glob")
@patch("pathlib.Path.iterdir")
@patch("builtins.open", new_callable=mock_open)
def test_collect_all_static_info_success(mock_open_func, mock_iterdir, mock_glob, mock_run_command, caplog):
    """
    Tests the success path of the v2.2 collector, with FULL filesystem isolation.
    """
    mock_run_command.side_effect = lambda cmd: {
        "sysctl": MOCK_SYSCTL_OUTPUT,
        "uname": MOCK_UNAME_OUTPUT,
        "ip": MOCK_IP_ADDR_OUTPUT,
    }.get(cmd.split()[0], "")

    mock_open_func.side_effect = lambda path, *args, **kwargs: {
        "/etc/os-release": mock_open(read_data=MOCK_OS_RELEASE_CONTENT).return_value,
        "/proc/cpuinfo": mock_open(read_data=MOCK_CPUINFO_CONTENT).return_value,
        "/proc/meminfo": mock_open(read_data=MOCK_MEMINFO_CONTENT).return_value,
    }.get(str(path), mock_open(read_data="").return_value)

    mock_cpu0_path = MagicMock()
    mock_cpu0_path.name = "cpu0"
    (mock_cpu0_path / "cpufreq/scaling_governor").exists.return_value = True
    (mock_cpu0_path / "cpufreq/scaling_governor").read_text.return_value = "performance"
    mock_glob.return_value = [mock_cpu0_path]

    mock_sda_path = MagicMock()
    mock_sda_path.name = "sda"
    child_map = {}

    def _div_child(name):
        if name not in child_map:
            child_map[name] = MagicMock()
        return child_map[name]

    mock_sda_path.__truediv__.side_effect = _div_child
    (child_map.setdefault("partition", MagicMock()).exists).return_value = False
    (child_map.setdefault("size", MagicMock()).read_text).return_value = "2000000"
    (child_map.setdefault("removable", MagicMock()).exists).return_value = True
    (child_map.setdefault("removable", MagicMock()).read_text).return_value = "0"
    (child_map.setdefault("device/model", MagicMock()).exists).return_value = True
    (child_map.setdefault("device/model", MagicMock()).read_text).return_value = "TestModel"
    (child_map.setdefault("queue/scheduler", MagicMock()).exists).return_value = True
    (child_map.setdefault("queue/scheduler", MagicMock()).read_text).return_value = "[mq-deadline] bfq"
    mock_iterdir.return_value = [mock_sda_path]

    result = _collect_all_static_info()

    assert result["os_info"]["NAME"] == "openEuler"
    assert result["cpu_info"]["CPU(s)"] == 2
    assert "MemTotal" in result["memory_info"]
    assert result["cpu_governor"]["unique_governors"] == ["performance"]
    assert result["disk_info"]["block_devices"][0]["model"] == "TestModel"
    assert result["io_scheduler"]["sda"] == "mq-deadline"
    assert "vm.swappiness" in result["kernel_parameters"]
    assert "error" not in result["net_info"]

    assert not caplog.records


@patch("src.pipa.commands.healthcheck.run_command")
@patch("pathlib.Path.exists", return_value=False)
@patch("builtins.open", side_effect=FileNotFoundError)
def test_collect_all_static_info_with_failures(mock_open_func, mock_exists, mock_run_command, caplog):
    """
    Tests graceful failure when underlying /proc or /sys files are missing.
    """
    from src.executor import ExecutionError

    mock_run_command.side_effect = ExecutionError("Command failed")

    result = _collect_all_static_info()

    assert result["os_info"] == {}
    assert "error" in result["disk_info"]
    assert "error" in result["net_info"]
    assert result["kernel_parameters"] == {}

    assert len(caplog.records) > 0
    assert any("Error reading /etc/os-release" in rec.message for rec in caplog.records)
    assert any("Could not collect sysctl parameters" in rec.message for rec in caplog.records)
