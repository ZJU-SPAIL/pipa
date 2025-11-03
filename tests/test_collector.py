import pytest
from src.collector import collect_cpu_utilization
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
