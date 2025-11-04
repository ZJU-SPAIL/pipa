# tests/integration/test_collector_integration.py

import pytest
import subprocess
import time
from src.collector import collect_perf_stat
from src.executor import ExecutionError

# Mark this whole file as 'integration' tests.
# We can run only unit tests with `pytest -m "not integration"`.
# 我们可以用 `pytest -m "not integration"` 来只运行单元测试。
pytestmark = pytest.mark.integration


@pytest.fixture
def target_process():
    """A pytest fixture to provide a simple, short-lived target process."""
    # Start a simple process in the background
    # 在后台启动一个简单的进程
    proc = subprocess.Popen(["sleep", "2"])

    # Give it a moment to start
    time.sleep(0.1)

    yield proc.pid

    # Teardown: ensure the process is terminated
    # 收尾：确保进程被终止
    if proc.poll() is None:
        proc.terminate()
        proc.wait()


def test_collect_perf_stat_integration(target_process):
    """
    Tests that collect_perf_stat can run a real perf command.
    测试 collect_perf_stat 能否运行一个真实的 perf 命令。

    This test requires `perf` to be installed and accessible.
    这个测试要求 perf 已被安装且可用。
    """
    # Use a minimal, universally available set of events
    # 使用一组最小的、普遍可用的事件
    events = ["cycles", "instructions"]

    try:
        # We are testing the real execution, so no monkeypatching
        # 我们在测试真实执行，所以没有 monkeypatching
        output = collect_perf_stat(target_pid=target_process, events=events, duration=1)

        # We don't assert for specific values, just that the report looks right.
        # 我们不断言具体的值，只断言报告看起来是正确的。
        assert "Performance counter stats for process id" in output
        assert "cycles" in output.lower()
        assert "instructions" in output.lower()
        assert "seconds time elapsed" in output

    except ExecutionError as e:
        # If perf is not installed or permission is denied, fail the test
        # with a helpful message.
        # 如果 perf 未安装或权限被拒绝，用一个有帮助的信息让测试失败。
        if "perf command not found" in str(e) or "Permission denied" in str(e):
            pytest.fail(
                "perf tool is not available or permissions are insufficient. "
                f"Skipping integration test. Error: {e}"
            )
        else:
            # For other errors, just re-raise
            # 对于其他错误，直接重新抛出
            raise
