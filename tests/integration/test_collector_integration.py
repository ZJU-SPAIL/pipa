# tests/integration/test_collector_integration.py

import subprocess
import time

import pytest

from src.collector import start_perf_stat, start_sar, stop_perf_stat, stop_sar
from src.executor import ExecutionError, PerfPermissionError

# Mark this whole file as 'integration' tests.
# We can run only unit tests with `pytest -m "not integration"`.
# 我们可以用 `pytest -m "not integration"` 来只运行单元测试。
pytestmark = pytest.mark.integration


@pytest.fixture
def temp_output_file(tmp_path):
    """Provides a temporary file path for test output."""
    return tmp_path / "perf_report.txt"


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


def test_collect_perf_stat_pid_mode_integration(target_process, temp_output_file):
    """
    Tests the 'pid' mode of collect_perf_stat with a real perf command.
    测试 collect_perf_stat 的 'pid' 模式与真实的 perf 命令的集成。
    """
    events = [["cycles", "instructions"]]
    proc = None
    try:
        proc = start_perf_stat(
            mode="pid",
            target_pid=target_process,
            output_file=str(temp_output_file),
            event_groups=events,
        )
        # Ensure the process was actually started
        assert proc is not None, "start_perf_stat should return a process handle."

        # Simulate sampling duration
        time.sleep(1)

    except ExecutionError as e:
        if "perf command not found" in str(e) or "Permission denied" in str(e):
            pytest.fail(
                "perf tool is not available or permissions are insufficient. " f"Skipping integration test. Error: {e}"
            )
        else:
            raise
    finally:
        if proc:
            stop_perf_stat(proc, str(temp_output_file), timeout=5)

    # Verification
    report_content = temp_output_file.read_text()
    assert "Performance counter stats for process id" in report_content
    assert "cycles" in report_content.lower()
    assert "instructions" in report_content.lower()


def test_collect_perf_stat_system_mode_integration(temp_output_file):
    """
    Tests the 'system' (-a) mode. Skips if perf permissions are insufficient.
    """
    events = [["cpu-clock", "page-faults"]]
    proc = None
    try:
        proc = start_perf_stat(
            mode="system",
            output_file=str(temp_output_file),
            event_groups=events,
        )
        assert proc is not None

        time.sleep(1)

    except ExecutionError as e:
        if "perf command not found" in str(e):
            pytest.fail(f"perf tool is not available. Error: {e}")
        else:
            raise
    finally:
        if proc:
            try:
                stop_perf_stat(proc, str(temp_output_file), timeout=5)
            except PerfPermissionError as e:
                # 如果捕获到我们自定义的权限错误，就跳过测试
                pytest.skip(f"Skipping due to perf permission error: {e}")

    report_content = temp_output_file.read_text()
    assert "Performance counter stats for 'system wide'" in report_content
    assert "cpu-clock" in report_content.lower()
    assert "page-faults" in report_content.lower()


def test_sar_integration(temp_output_file):
    """
    Tests the full start/stop cycle of the sar collector.
    """
    proc = None
    duration = 2
    interval = 1

    try:
        proc = start_sar(duration=duration, interval=interval, output_file=str(temp_output_file))
        assert proc is not None, "start_sar should return a process handle."

        content = stop_sar(proc, str(temp_output_file), duration=duration)

        assert content is not None
        assert "Linux" in content
        assert "CPU" in content
        assert "%usr" in content

    except ExecutionError as e:
        if "sar command not found" in str(e):
            pytest.fail(f"sar tool is not available, skipping integration test: {e}")
        else:
            raise
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5)

    report_content = temp_output_file.read_text()
    assert "Linux" in report_content
    assert "CPU" in report_content
