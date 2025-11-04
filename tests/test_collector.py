import pytest
from src.collector import collect_cpu_utilization, collect_perf_stat
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
    monkeypatch.setattr(
        "src.collector.run_command", lambda command, env: SAR_OUTPUT_NORMAL
    )

    # The new logic directly parses the Average line.
    # 新的逻辑直接解析 Average 行。
    # Expected result is %user (15.00) + %system (7.50)
    # 期望的结果是 %user (15.00) + %system (7.50)
    expected_avg = 22.5

    avg_util = collect_cpu_utilization(duration=2)

    assert avg_util == pytest.approx(expected_avg)


def test_collect_cpu_utilization_no_average_line(monkeypatch):
    """
    Tests that an error is raised if the "Average:" line is not found.
    测试在找不到 "Average:" 行时是否会引发错误。
    """
    monkeypatch.setattr(
        "src.collector.run_command", lambda command, env: SAR_OUTPUT_NO_AVERAGE
    )

    # We expect this to raise an ExecutionError with the new error message.
    # 我们期望这里会引发一个带有新错误信息的 ExecutionError。
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


def test_collect_perf_stat_success(monkeypatch):
    """
    Tests successful collection and parsing of perf stat output from stderr.
    测试从 stderr 成功收集和解析 perf stat 的输出。
    """

    class MockCompletedProcess:
        """Mocks the result of subprocess.run."""

        stderr = PERF_OUTPUT_NORMAL
        stdout = ""
        returncode = 0

        def check_returncode(self):
            pass

    # We need to mock subprocess.run for this specific function
    # 我们需要为这个特定的函数模拟 subprocess.run
    monkeypatch.setattr(
        "src.collector.subprocess.run", lambda *args, **kwargs: MockCompletedProcess()
    )

    events = ["cycles", "instructions", "branches", "branch-misses"]
    result = collect_perf_stat(target_pid=12345, events=events, duration=1)

    assert "cycles" in result
    assert "instructions" in result
    assert "2.00  insn per cycle" in result
    assert result == PERF_OUTPUT_NORMAL


def test_collect_perf_stat_command_construction(monkeypatch):
    """
    Tests that the perf stat command is constructed correctly.
    测试 perf stat 命令是否被正确地构建。
    """
    # This list will store the command that was actually called
    # 这个列表将存储实际被调动的命令
    called_command = []

    class MockCompletedProcess:
        stderr = "Success"
        returncode = 0

    def mock_run(*args, **kwargs):
        # The first argument to subprocess.run is the command list
        # subprocess.run 的第一个参数就是命令列表
        called_command.extend(args[0])
        return MockCompletedProcess()

    monkeypatch.setattr("src.collector.subprocess.run", mock_run)

    events = ["cycles", "instructions"]
    collect_perf_stat(target_pid=999, events=events, duration=5)

    # Reconstruct the expected command for comparison
    # 重构期望的命令以进行比较
    expected_command = "perf stat -p 999 -e cycles,instructions -- sleep 5"

    assert " ".join(called_command) == expected_command


def test_collect_perf_stat_no_events():
    """
    Tests that the function handles an empty event list gracefully.
    测试函数能优雅地处理空的事件列表。
    """
    # No monkeypatching needed as it should return before calling subprocess
    # 不需要 monkeypatching，因为它应该在调用子进程前就返回
    result = collect_perf_stat(target_pid=12345, events=[], duration=1)
    assert "No perf events specified" in result
