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


@pytest.mark.parametrize(
    "mode, kwargs_for_call, expected_flag_part",
    [
        ("pid", {"target_pid": 999}, "-p 999"),
        ("cpu", {"target_cpus": "0-3,7"}, "-C 0-3,7"),
        ("system", {}, "-a"),
    ],
)
def test_collect_perf_stat_command_construction(
    monkeypatch, mode, kwargs_for_call, expected_flag_part
):
    """
    Tests that the perf stat command is constructed correctly for all modes.
    测试 perf stat 命令是否能为所有模式正确地构建。
    """
    called_command = []

    def mock_run_command(command):
        called_command.append(command)
        # We don't need a real result, just to capture the command
        return "mock output"

    monkeypatch.setattr("src.collector.run_command", mock_run_command)

    # Mock run_in_background to do the same thing: just record the command
    # 让 run_in_background 也做同样的事：只记录命令
    # It needs to return a dummy Popen-like object though
    # 但它需要返回一个假的、像 Popen 的对象
    class MockPopen:
        def poll(self):
            return None

        def terminate(self):
            pass

        def wait(self, timeout=None):
            pass

        def send_signal(self, sig):
            pass

    def mock_run_in_background(command):
        called_command.append(command)
        return MockPopen()

    monkeypatch.setattr("src.collector.run_in_background", mock_run_in_background)

    # Base arguments, merged with mode-specific ones
    base_args = {
        "duration": 5,
        "output_file": "/tmp/perf.txt",
        "event_groups": [["cycles"]],
    }
    collect_perf_stat(mode=mode, **base_args, **kwargs_for_call)

    # The command is the first (and only) item in the list
    final_command = called_command[0]
    assert expected_flag_part in final_command
    assert "-o /tmp/perf.txt" in final_command
    assert "--append" in final_command
    assert "-e {cycles}" in final_command
    if mode == "system":
        assert "-- sleep 5" in final_command


@pytest.mark.parametrize(
    "mode, kwargs_for_call, expected_error_msg",
    [
        ("invalid_mode", {}, "Invalid perf stat mode: invalid_mode"),
        ("pid", {}, "target_pid parameter is required for 'pid' mode."),
        ("cpu", {}, "target_cpus parameter is required for 'cpu' mode."),
    ],
)
def test_collect_perf_stat_raises_value_error_for_invalid_params(
    mode, kwargs_for_call, expected_error_msg
):
    """
    Tests that ValueError is raised for invalid mode or missing parameters.
    测试在模式无效或参数缺失时，是否会引发 ValueError。
    """
    base_args = {
        "duration": 1,
        "output_file": "dummy.txt",
        "event_groups": [["cycles"]],
    }
    with pytest.raises(ValueError, match=expected_error_msg):
        collect_perf_stat(mode=mode, **base_args, **kwargs_for_call)


def test_collect_perf_stat_success_path(monkeypatch):
    """
    Tests the successful execution path still works.
    测试成功执行的路径依然有效。
    """
    # This test now simply ensures run_command is called and no error occurs.
    # The actual command construction is tested above.
    # 这个测试现在只简单确保 run_command 被调用且不发生错误。
    # 实际的命令构建已在上面测试过。
    mock_calls = []

    def mock_run_command(command):
        mock_calls.append(command)
        return "Success"

    monkeypatch.setattr("src.collector.run_command", mock_run_command)

    collect_perf_stat(
        mode="system",
        duration=1,
        output_file="dummy.txt",
        event_groups=[["instructions"]],
    )

    assert len(mock_calls) == 1
    assert "perf stat -a" in mock_calls[0]
