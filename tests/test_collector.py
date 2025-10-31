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

SAR_OUTPUT_NO_DATA = """
Linux 5.15.0-generic (my-laptop)   10/31/2025   _x86_64_    (16 CPU)

12:00:01     CPU     %user     %nice   %system   %iowait    %steal     %idle
Average:        all     0.00      0.00      0.00      0.00      0.00     100.00
"""


def test_collect_cpu_utilization_success(monkeypatch):
    """
    Tests successful parsing of normal sar output.
    测试对正常 sar 输出的成功解析。
    """
    # We "monkeypatch" the run_command function.
    # When our code calls run_command, it will execute this lambda instead.
    # 我们“猴子补丁”了 run_command 函数。
    # 当我们的代码调用 run_command 时，它将执行这个 lambda 表达式。
    monkeypatch.setattr(
        "src.collector.run_command", lambda command, env: SAR_OUTPUT_NORMAL
    )

    # Expected result is the average of (10.00 + 5.00) and (20.00 + 10.00)
    # 期望的结果是 (10.00 + 5.00) 和 (20.00 + 10.00) 的平均值
    # (15 + 30) / 2 = 22.5
    expected_avg = 22.5

    avg_util = collect_cpu_utilization(duration=2)

    # pytest.approx handles floating point comparisons
    # pytest.approx 用于处理浮点数的比较
    assert avg_util == pytest.approx(expected_avg)


def test_collect_cpu_utilization_no_data(monkeypatch):
    """
    Tests that an error is raised if no data lines are found.
    测试在找不到数据行时是否会引发错误。
    """
    monkeypatch.setattr(
        "src.collector.run_command", lambda command, env: SAR_OUTPUT_NO_DATA
    )

    # We expect this to raise an ExecutionError
    # 我们期望这里会引发一个 ExecutionError
    with pytest.raises(ExecutionError, match="No valid CPU data lines found"):
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
