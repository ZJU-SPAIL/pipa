import logging

import pytest

from src.pipa.commands.healthcheck import _collect_all_static_info

MOCK_OS_INFO = 'NAME="Ubuntu"\nVERSION_ID="20.04"'
MOCK_KERNEL_INFO = "Linux 5.10.0 aarch64"
MOCK_CPU_INFO = "CPU(s): 8\nModel name: ARMv8"
MOCK_NUMA_INFO = "available: 2 nodes (0-1)\nnode 0 cpus: 0 1 2 3\n"


# --- 模拟 run_command 成功情况 ---
def mock_run_command_success(command, **kwargs):
    if "os-release" in command:
        return MOCK_OS_INFO
    if "uname -a" in command:
        return MOCK_KERNEL_INFO
    if "lscpu" in command:
        return MOCK_CPU_INFO
    if "numactl --hardware" in command:
        return MOCK_NUMA_INFO
    return ""


def mock_run_command_with_errors(command, **kwargs):
    if "os-release" in command:
        return MOCK_OS_INFO
    if "lscpu" in command:
        return "Error collecting CPU info: ExecutionError('lscpu failed')"
    if "numactl --hardware" in command:
        return "Error collecting NUMA info: Command not found"
    return ""


@pytest.fixture(autouse=True)
def setup_logging_for_test():
    """Set log level to ERROR for cleaner test output."""
    logging.getLogger("src.pipa.commands.healthcheck").setLevel(logging.ERROR)


def test_collect_all_static_info_success(monkeypatch):
    """测试在成功路径下，所有静态信息都能被成功收集。"""
    monkeypatch.setattr("src.pipa.commands.healthcheck.run_command", mock_run_command_success)

    result = _collect_all_static_info()

    assert result["os_info"]["NAME"] == "Ubuntu"
    assert result["cpu_info"]["CPUs_Count"] == 8
    assert "numa_info" in result
    assert result["numa_info"]["available"] == "2 nodes (0-1)"


def test_collect_all_static_info_with_failures(monkeypatch):
    """测试采集器能优雅地处理部分命令的失败情况。"""
    monkeypatch.setattr("src.pipa.commands.healthcheck.run_command", mock_run_command_with_errors)

    result = _collect_all_static_info()

    assert result["os_info"]["NAME"] == "Ubuntu"
    assert "error" in result["cpu_info"]
    assert "lscpu failed" in result["cpu_info"]["error"]
    assert "error" in result["numa_info"]
