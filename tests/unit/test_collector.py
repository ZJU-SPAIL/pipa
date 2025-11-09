import subprocess
from typing import cast

import pytest

from src.collector import (
    collect_cpu_utilization,
    start_perf_stat,
    start_sar,
    stop_perf_stat,
    stop_sar,
)
from src.executor import ExecutionError

# This is a sample output from `LC_ALL=C sar -u 1 5`
# 这是一个 `LC_ALL=C sar -u 1 5` 的示例输出
# It contains a header, data lines, and an average line.
# 它包含表头、数据行和平均值行。
SAR_OUTPUT_NORMAL = """
Linux 5.15.0-generic (my-laptop)   10/31/2025   _x86_64_    (16 CPU)

12:00:01     CPU     %user     %nice   %system   %iowait    %steal     %idle
12:00:02     all     10.00      0.00      5.00      0.00      0.00     85.00
12:00:03     all     20.00      0.00     10.00      0.00      0.00     70.00
Average:        all     15.00      0.00      7.50      0.00      0.00     77.50
"""

# New mock data for the refactored test case
# 为重构后的测试用例准备的新的模拟数据
SAR_OUTPUT_NO_AVERAGE = """
Linux 5.15.0-generic (my-laptop)   10/31/2025   _x86_64_    (16 CPU)

12:00:01     CPU     %user     %nice   %system   %iowait    %steal     %idle
12:00:02     all     10.00      0.00      5.00      0.00      0.00     85.00
"""


def test_collect_cpu_utilization_success(monkeypatch):
    """
    Tests successful parsing of normal sar output by reading the Average line.
    测试通过读取 Average 行，成功解析正常的 sar 输出。
    """
    monkeypatch.setattr("src.collector.run_command", lambda command, env: SAR_OUTPUT_NORMAL)

    expected_avg = 22.5

    avg_util = collect_cpu_utilization(duration=2)

    assert avg_util == pytest.approx(expected_avg)


def test_collect_cpu_utilization_no_average_line(monkeypatch):
    """
    Tests that an error is raised if the "Average:" line is not found.
    测试在找不到 "Average:" 行时是否会引发错误。
    """
    monkeypatch.setattr("src.collector.run_command", lambda command, env: SAR_OUTPUT_NO_AVERAGE)

    with pytest.raises(ExecutionError, match="Could not find 'Average:' line"):
        collect_cpu_utilization(duration=1)


def test_collect_cpu_utilization_command_fails(monkeypatch):
    """
    Tests that the underlying ExecutionError is propagated.
    测试底层的 ExecutionError 是否被正确地传递上来。
    """

    def mock_run_command_failure(command, env):
        raise ExecutionError("sar command failed!")

    monkeypatch.setattr("src.collector.run_command", mock_run_command_failure)

    with pytest.raises(ExecutionError, match="sar command failed"):
        collect_cpu_utilization(duration=1)


# --- Unit tests for collect_perf_stat ---

# Mock stderr output from a successful `perf stat` command
# 模拟 `perf stat` 命令成功执行后的 stderr 输出
PERF_OUTPUT_NORMAL = """
 Performance counter stats for process id 12345:

          1,234.56 msec task-clock                #    1.000 CPUs utilized
             1,234      context-switches          #    0.001 M/sec
                87      cpu-migrations            #    0.070 K/sec
               345      page-faults               #    0.279 K/sec
     3,000,000,000      cycles                    #    2.430 GHz
     6,000,000,000      instructions              #    2.00  insn per cycle
       600,000,000      branches                  #  486.000 M/sec
        12,000,000      branch-misses             #    2.00% of all branches

       1.234567890 seconds time elapsed
"""


@pytest.mark.parametrize(
    "mode, kwargs_for_call, expected_flag_part",
    [
        ("pid", {"target_pid": 999}, "-p 999"),
        ("cpu", {"target_cpus": "0-3,7"}, "-C 0-3,7"),
        ("system", {}, "-a"),
        ("system", {"interval": 1000}, "-I 1000"),
    ],
)
def test_start_perf_stat_command_construction(monkeypatch, mode, kwargs_for_call, expected_flag_part):
    """
    Tests that the perf stat command is constructed correctly for all modes
    by the new start_perf_stat function.
    """
    called_command_list = []

    def mock_popen(command_list, **kwargs):
        called_command_list.append(command_list)

        class MockPopen:
            pid = 123

            def poll(self):
                return None

        return MockPopen()

    monkeypatch.setattr("src.collector.subprocess.Popen", mock_popen)

    base_args = {
        "output_file": "/tmp/perf.txt",
        "event_groups": [["cycles"]],
    }
    start_perf_stat(mode=mode, **base_args, **kwargs_for_call)

    assert len(called_command_list) == 1
    final_command = " ".join(called_command_list[0])

    assert "perf stat" in final_command
    assert expected_flag_part in final_command
    assert "--append" not in final_command
    assert "-e '{cycles}'" in final_command
    assert "sleep" not in final_command


@pytest.mark.parametrize(
    "mode, kwargs, expected_error_msg",
    [
        ("invalid_mode", {}, "Invalid perf stat mode: invalid_mode"),
        ("pid", {}, "Missing required parameter for perf stat mode 'pid'."),
        ("cpu", {}, "Missing required parameter for perf stat mode 'cpu'."),
    ],
)
def test_start_perf_stat_raises_value_error_for_invalid_params(mode, kwargs, expected_error_msg):
    """
    Tests that ValueError is raised for invalid mode or missing parameters.
    """
    with pytest.raises(ValueError, match=expected_error_msg):
        start_perf_stat(mode=mode, output_file="dummy.txt", event_groups=[["cycles"]], **kwargs)


class MockPopen:
    def __init__(self, pid=123, stderr_data="perf data", should_timeout=False):
        self.pid = pid
        self._stderr_data = stderr_data
        self._should_timeout = should_timeout
        self.killed = False

    def send_signal(self, sig):
        """Mock send_signal method."""
        pass

    def communicate(self, timeout=None):
        if self._should_timeout and not self.killed:
            raise subprocess.TimeoutExpired("cmd", timeout or 0)
        return (None, self._stderr_data)

    def kill(self):
        self.killed = True

    def poll(self):  # stop_perf_stat 可能会调用 poll
        return None


def test_stop_perf_stat_success(monkeypatch, tmp_path):
    """Tests stop_perf_stat with a successful communicate() call."""
    mock_proc = MockPopen(stderr_data="cycles: 100")
    written_content = []
    temp_file = tmp_path / "perf_output.txt"

    def mock_open(*args, **kwargs):
        class MockFile:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                pass

            def write(self, content):
                written_content.append(content)

        return MockFile()

    monkeypatch.setattr("builtins.open", mock_open)

    content = stop_perf_stat(cast(subprocess.Popen, mock_proc), str(temp_file), timeout=5)

    assert content == "cycles: 100"
    assert written_content[0] == "cycles: 100"
    assert mock_proc.killed is False


def test_stop_perf_stat_timeout(tmp_path):
    """Tests stop_perf_stat's behavior on communicate() timeout."""
    mock_proc = MockPopen(should_timeout=True, stderr_data="partial data")
    temp_file = tmp_path / "perf_output.txt"

    content = stop_perf_stat(cast(subprocess.Popen, mock_proc), str(temp_file), timeout=5)

    assert mock_proc.killed is True
    assert content == "partial data"
    assert temp_file.exists()
    assert temp_file.read_text() == "partial data"


# --- Unit tests for start_sar and stop_sar ---
class MockSarPopen:
    def __init__(
        self,
        pid=123,
        stdout_data="sar output data",
        stderr_data="perf data",
        should_timeout=False,
        returncode=0,
    ):
        self.pid = pid
        self._stdout_data = stdout_data
        self._stderr_data = stderr_data
        self._should_timeout = should_timeout
        self.killed = False
        self.returncode = returncode
        self.terminated = False

    def send_signal(self, sig):
        """Mock send_signal method."""
        pass

    def communicate(self, timeout=None):
        if self._should_timeout and not self.killed:
            raise subprocess.TimeoutExpired("cmd", timeout or 0)
        return (self._stdout_data, self._stderr_data)

    def kill(self):
        self.killed = True

    def poll(self):
        return None

    def terminate(self):
        self.terminated = True


def test_start_sar_command_construction(monkeypatch):
    """Tests that the sar command is constructed correctly."""
    called_command = []

    def mock_popen(command_list, **kwargs):
        called_command.extend(command_list)

        class MockSarPopen:
            pid = 123

        return MockSarPopen()

    monkeypatch.setattr("subprocess.Popen", mock_popen)

    start_sar(duration=10, interval=2, output_file="dummy.txt")

    assert "sar" in called_command
    assert "-A" in called_command
    assert "2" in called_command
    assert len(called_command) == 3


def test_start_sar_skips_if_duration_too_short():
    """Tests that sar is skipped if duration is less than interval."""
    proc = start_sar(duration=1, interval=2, output_file="dummy.txt")
    assert proc is None


def test_stop_sar_success(monkeypatch, tmp_path):
    """Tests stop_sar success path with mocked process."""
    mock_proc = MockSarPopen(stdout_data="sar output data")
    temp_file = tmp_path / "sar_output.txt"

    content = stop_sar(cast(subprocess.Popen, mock_proc), str(temp_file), duration=5)

    assert content == "sar output data"
    assert temp_file.read_text() == "sar output data"
    assert mock_proc.terminated is True
