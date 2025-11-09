import subprocess
from typing import cast
from unittest.mock import MagicMock, patch

from src.collector import (
    start_perf_stat,
    start_sar,
    stop_perf_stat,
    stop_sar,
)


@patch("src.collector.platform.machine", return_value="x86_64")
@patch("src.collector.subprocess.Popen")
def test_start_perf_stat_uses_defaults(mock_popen, mock_machine):
    """Test that start_perf_stat correctly uses default values and builds the command."""
    start_perf_stat(target_pid="999")

    mock_popen.assert_called_once()
    final_command = " ".join(mock_popen.call_args[0][0])

    assert "perf stat" in final_command
    assert "-p 999" in final_command
    assert "-I 1000" in final_command
    assert "-A" in final_command
    assert "cycles,instructions" in final_command


@patch("src.collector.platform.machine", return_value="aarch64")
@patch("src.collector.subprocess.Popen")
def test_start_perf_stat_uses_aarch64_events(mock_popen, mock_machine):
    """Test that start_perf_stat switches to aarch64 events based on architecture."""
    start_perf_stat(target_pid="999")
    final_command = " ".join(mock_popen.call_args[0][0])
    assert "cpu-cycles,instructions" in final_command


@patch("src.collector.subprocess.Popen")
def test_start_perf_stat_with_overrides(mock_popen):
    """Test that overrides for interval and events work correctly."""
    start_perf_stat(target_pid="999", interval=500, events_override_str="my_event1,my_event2")

    final_command = " ".join(mock_popen.call_args[0][0])
    assert "-I 500" in final_command
    assert "my_event1,my_event2" in final_command
    assert "cycles" not in final_command


class MockPopen:
    def __init__(self, pid=123, stderr_data="perf data", should_timeout=False, returncode=0):
        self.pid = pid
        self._stderr_data = stderr_data
        self._should_timeout = should_timeout
        self.killed = False
        self.returncode = returncode

    def send_signal(self, sig):
        pass

    def communicate(self, timeout=None):
        if self._should_timeout and not self.killed:
            raise subprocess.TimeoutExpired("cmd", timeout or 0)
        return (None, self._stderr_data)

    def kill(self):
        self.killed = True

    def poll(self):
        return None


def test_stop_perf_stat_success(tmp_path):
    mock_proc = MockPopen(stderr_data="cycles: 100")
    temp_file = tmp_path / "perf_output.txt"
    content = stop_perf_stat(cast(subprocess.Popen, mock_proc), str(temp_file), timeout=5)
    assert content == "cycles: 100"
    assert temp_file.read_text() == "cycles: 100"


@patch("subprocess.Popen")
def test_start_sar_command_construction(mock_popen):
    start_sar(duration=10, interval=2, output_bin_file="dummy.bin")
    mock_popen.assert_called_once()
    called_args = mock_popen.call_args.args[0]
    assert "sar" in called_args
    assert "-A" in called_args
    assert "-o" in called_args
    assert "dummy.bin" in called_args
    assert "2" in called_args
    assert "6" in called_args


def test_start_sar_skips_if_duration_too_short():
    proc = start_sar(duration=1, interval=2, output_bin_file="dummy.bin")
    assert proc is None


@patch("src.collector.run_command")
@patch("builtins.open")
def test_stop_sar_success(mock_open, mock_run_command, tmp_path):
    mock_proc = MockPopen()
    mock_file_handler = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file_handler
    mock_run_command.return_value = "hostname;iface;timestamp;CPU;%user"

    bin_file = tmp_path / "sar.bin"
    csv_file = tmp_path / "sar.csv"

    stop_sar(
        proc=cast(subprocess.Popen, mock_proc),
        output_bin_file=str(bin_file),
        output_csv_file=str(csv_file),
        timeout=10,
    )

    mock_run_command.assert_called_once_with(f"sadf -P ALL -d -- {str(bin_file)}")
    mock_open.assert_called_once_with(str(csv_file), "w")
    mock_file_handler.write.assert_called_once_with("hostname;iface;timestamp;CPU;%user")
