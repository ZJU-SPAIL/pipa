# src/collector.py

import logging
import os
import shlex
import signal
import subprocess
from typing import Optional, Union

from .executor import (
    ExecutionError,
    PerfPermissionError,
    run_command,
)

log = logging.getLogger(__name__)


def start_perf_stat(
    output_file: str,
    mode: str = "pid",
    target_pid: Optional[Union[int, str]] = None,
    target_cpus: Optional[str] = None,
    event_groups: Optional[list[list[str]]] = None,
    all_threads: bool = False,
    interval: Optional[int] = None,
) -> Optional[subprocess.Popen]:
    """
    Starts perf stat in the background. Its stderr is piped for capture.
    在后台启动 perf stat，其 stderr 被管道捕获。
    :param duration: The total duration to monitor in seconds.
    :param output_file: The file to save the perf stat report.
    :param mode: The collection mode: "pid", "cpu", or "system".
    :param target_pid: The process ID to monitor (for "pid" mode).
    :param target_cpus: A string of CPUs to monitor, e.g., "0,2-4" (for "cpu" mode).
    :param event_groups: A list of event groups,
    :param interval: The interval between samples in milliseconds (for -I option).
    e.g., [["cycles", "ins"], ["branches"]].
    :raises ExecutionError: If the perf command fails.
    :raises ValueError: If parameters are invalid for the selected mode.
    """
    if not event_groups:
        log.warning("No perf event groups specified. Skipping perf stat.")
        return None

    target_flag_builders = {
        "pid": lambda: f"-p {target_pid}" if target_pid else None,
        "cpu": lambda: f"-C {target_cpus}" if target_cpus else None,
        "system": lambda: "-a",
    }

    if mode not in target_flag_builders:
        raise ValueError(f"Invalid perf stat mode: {mode}")

    target_flag = target_flag_builders[mode]()
    if not target_flag:
        raise ValueError(f"Missing required parameter for perf stat mode '{mode}'.")

    events_flags = []
    for group in event_groups:
        if group:
            events_str = ",".join(group)
            events_flags.append(f"-e '{{{events_str}}}'")

    command_parts = [
        "perf",
        "stat",
        target_flag,
        *events_flags,
    ]
    if mode in ["system", "cpu"]:
        command_parts.append("-A")
    if interval is not None:
        command_parts.append(f"-I {interval}")

    log.info(f"Starting background perf stat: {' '.join(command_parts)}")
    try:
        proc = subprocess.Popen(
            command_parts,
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid,
        )
        return proc
    except FileNotFoundError:
        raise ExecutionError("Command not found: perf")


# 修改 stop_perf_stat 函数的签名和实现
def stop_perf_stat(proc: subprocess.Popen, output_file: str, timeout: int) -> Optional[str]:
    """
    Stops perf stat, captures its stderr, writes to file, and returns the content.
    停止 perf stat，捕获其 stderr，写入文件，并返回内容。
    """
    log.info(f"Sending SIGINT to perf stat process (PID: {proc.pid})...")
    proc.send_signal(signal.SIGINT)

    log.info("Waiting for perf stat to finish and output results...")
    try:
        _, stderr_output = proc.communicate(timeout=timeout)
        if "perf_event_paranoid" in stderr_output:
            error_msg = (
                "Perf permission denied. The kernel's perf_event_paranoid setting "
                "is too restrictive.\n"
                "To fix this temporarily, run:\n"
                "    echo -1 | sudo tee /proc/sys/kernel/perf_event_paranoid\n"
                "To make the change permanent, add 'kernel.perf_event_paranoid = -1' "
                "to /etc/sysctl.conf"
            )
            raise PerfPermissionError(error_msg)
        log.info("perf stat process stopped and output captured.")

        try:
            with open(output_file, "w") as f:
                f.write(stderr_output)
            log.info(f"perf stat report saved to {output_file}")
        except IOError as e:
            log.error(f"Failed to write perf stat report to {output_file}: {e}")

        return stderr_output

    except subprocess.TimeoutExpired:
        log.warning("perf stat process did not respond to SIGINT. Killing it...")
        proc.kill()
        _, stderr_output = proc.communicate()

        if stderr_output:
            try:
                with open(output_file, "w") as f:
                    f.write(stderr_output)
                log.info(f"perf stat partial output saved to {output_file}")
            except IOError as e:
                log.error(f"Failed to write perf stat output to {output_file}: {e}")

        return stderr_output or "Process killed, no output captured."


def start_sar(
    duration: int,
    interval: int,
    output_bin_file: str,
) -> Optional[subprocess.Popen]:
    """
    Starts `sar -A` in the background, writing binary data to an output file.
    This is more robust than capturing stdout.
    在后台启动 `sar -A`，将二进制数据写入输出文件。这比捕获 stdout 更健壮。
    """
    if duration < interval:
        log.warning(f"Duration ({duration}) is less than interval ({interval}), skipping sar.")
        return None

    count = (duration // interval) + 1
    command = f"sar -A -o {shlex.quote(output_bin_file)} {interval} {count}"

    log.info(f"Starting background sar (binary mode): {command}")
    try:
        env = os.environ.copy()
        env["LC_ALL"] = "C"
        proc = subprocess.Popen(
            shlex.split(command),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        return proc
    except FileNotFoundError:
        raise ExecutionError("Command not found: sar")


def stop_sar(
    proc: subprocess.Popen,
    output_bin_file: str,
    output_csv_file: str,
    timeout: int,
) -> None:
    """
    Waits for sar to finish, then converts its binary output to CSV using sadf.
    等待 sar 结束，然后使用 sadf 将其二进制输出转换为 CSV。
    """
    log.info(f"Waiting for sar process (PID: {proc.pid}) to complete...")
    try:
        _, stderr_data = proc.communicate(timeout=timeout)
        if proc.returncode != 0:
            log.warning(f"sar process exited with code {proc.returncode}. Stderr: {stderr_data}")
    except subprocess.TimeoutExpired:
        log.warning(f"sar process timed out after {timeout}s. Killing it...")
        proc.kill()
        proc.communicate()

    log.info("Sar process finished. Converting binary output to CSV...")
    sadf_command = f"sadf -d -h -- {shlex.quote(output_bin_file)}"
    try:
        csv_output = run_command(sadf_command)
        with open(output_csv_file, "w") as f:
            f.write(csv_output)
        log.info(f"Successfully converted sar data to CSV: {output_csv_file}")
    except (ExecutionError, FileNotFoundError) as e:
        log.error(f"Failed to convert sar data to CSV using sadf: {e}")
    except IOError as e:
        log.error(f"Failed to write sar CSV file to {output_csv_file}: {e}")
