# # tests/unit/test_static_collector.py

import logging

import pytest

from src.executor import ExecutionError
from src.static_collector import collect_all_static_info, get_numa_info


# 确保在测试环境中不打印 click 输出
def mock_click_echo(*args, **kwargs):
    pass


@pytest.fixture(autouse=True)
def setup_logging_for_test():
    """Set log level to ERROR for cleaner test output."""
    logging.getLogger("src.static_collector").setLevel(logging.ERROR)


# --- 1. Mock 原始命令输出数据 (最终修正 MOCK_DF_INFO 以匹配目标平台) ---

MOCK_OS_INFO = 'NAME="Ubuntu"\nVERSION_ID="20.04"\nPRETTY_NAME="Ubuntu 20.04.6 LTS"'
MOCK_KERNEL_INFO = "Linux 5.10.0-10-generic #10-Ubuntu aarch64"
MOCK_CPU_INFO = "CPU(s): 8\nModel name: ARMv8\nCPU max MHz: 2500"
MOCK_MEM_INFO = "MemTotal: 16384000 kB\n" "MemFree: 800000 kB\n" "SwapCached: 0 kB"
# *** 最终修正 MOCK_DF_INFO：使用目标平台的格式和内容，确保 split() 列数一致 ***
MOCK_DF_INFO = (
    "Filesystem Size Used Avail Use% Mounted on\n"
    "/dev/mapper/openEuler-root 98G 15G 79G 16% /\n"
    "tmpfs 126G 19M 126G 1% /tmp"
)
MOCK_LSBLK_INFO = "NAME MAJ:MIN RM   SIZE RO TYPE MOUNTPOINT\n" "sda  8:0    0   100G  0 disk /"
MOCK_NMCLI_INFO = "3: eth0\n" "GENERAL.DEVICE: eth0\n" "GENERAL.TYPE: ethernet\n" "GENERAL.STATE: 10 (unmanaged)\n"
MOCK_NUMA_INFO = (
    "available: 2 nodes (0-1)\n"
    "node 0 cpus: 0 1 2 3\n"
    "node 0 size: 64 GB\n"
    "node 1 cpus: 4 5 6 7\n"
    "node 1 size: 64 GB"
)


# --- 2. 模拟 run_command 成功情况 ---


def mock_run_command_success(command, **kwargs):
    """Simulates successful command execution with structured mock data."""
    if "os-release" in command:
        return MOCK_OS_INFO
    if "uname -a" == command:
        return MOCK_KERNEL_INFO
    if "lscpu" in command:
        return MOCK_CPU_INFO
    if "meminfo" in command:
        return MOCK_MEM_INFO
    if "df -h" == command:
        return MOCK_DF_INFO
    if "lsblk" == command:
        return MOCK_LSBLK_INFO
    if "nmcli device show" == command:
        return MOCK_NMCLI_INFO
    if "numactl --hardware" == command:
        return MOCK_NUMA_INFO
    return ""


# --- 3. 测试用例 ---


def test_collect_all_static_info_success(monkeypatch):
    """
    测试在成功路径下，所有静态信息都能被成功收集，并验证其解析结构。
    """
    monkeypatch.setattr("src.static_collector.run_command", mock_run_command_success)

    result = collect_all_static_info()

    assert result["os_info"]["NAME"] == "Ubuntu"

    assert result["cpu_info"]["CPUs_Count"] == 8

    assert len(result["disk_info"]["Filesystem_Usage"]) == 2
    assert result["disk_info"]["Filesystem_Usage"][0]["Filesystem"] == "/dev/mapper/openEuler-root"
    assert result["disk_info"]["Filesystem_Usage"][0]["Size"] == "98G"
    assert "sda" in result["disk_info"]["Block_Devices_Raw"][1]

    assert result["numa_info"]["available"] == "2 nodes (0-1)"


def test_collect_all_static_info_with_failures(monkeypatch):
    """
    测试采集器能优雅地处理部分命令的失败情况，并返回结构化的错误字典。
    """

    def mock_run_command_with_errors(command, **kwargs):
        if "os-release" in command:
            return MOCK_OS_INFO
        if "lscpu" in command:
            return "Error collecting CPU info: ExecutionError('lscpu failed to run')"
        if "df -h" == command:
            raise ExecutionError("df permission denied")
        if "lsblk" == command:
            return MOCK_LSBLK_INFO
        return MOCK_KERNEL_INFO

    monkeypatch.setattr("src.static_collector.run_command", mock_run_command_with_errors)

    result = collect_all_static_info()

    assert result["cpu_info"]["error"].startswith("Error collecting CPU info: ExecutionError")

    assert result["disk_info"]["Filesystem_Usage"] == []
    assert "sda" in result["disk_info"]["Block_Devices_Raw"][1]


def test_get_numa_info_command_not_found(monkeypatch):
    """
    测试 numactl 命令未找到时的特定失败场景，确保返回结构化错误。
    """

    def mock_fail(command):
        if "numactl" in command:
            raise ExecutionError("numactl not installed or failed")
        return ""

    monkeypatch.setattr("src.static_collector.run_command", mock_fail)

    result = get_numa_info()

    assert "error" in result
    assert "'numactl' command failed or not found" in result["error"]
