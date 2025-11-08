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
    run_in_background,
)

log = logging.getLogger(__name__)


def collect_cpu_utilization(duration: int, interval: int = 1) -> float:
    """
    Collects average CPU utilization over a period using sar.
    在一段时间内，使用 sar 收集平均 CPU 利用率。

    :param duration: The total duration to monitor in seconds.
    :param interval: The interval between samples in seconds.
    :return: The average total CPU utilization (%user + %system).
    :raises ExecutionError: If sar command fails or output is unparsable.
    """
    count = duration // interval
    command = f"sar -u {interval} {count}"

    env = {"LC_ALL": "C"}

    output = ""

    try:
        output = run_command(command, env=env)
        lines = output.strip().splitlines()

        avg_line = None
        for line in reversed(lines):
            if line.strip().startswith("Average:"):
                avg_line = line
                break

        if not avg_line:
            raise ExecutionError("Could not find 'Average:' line in sar output.")

        log.debug(f"Line being parsed is: '{avg_line.strip()}'")

        parts = avg_line.split()
        if len(parts) < 5 or parts[1] != "all":
            raise ExecutionError("Unexpected format for 'Average:' line in sar output.")

        user_cpu = float(parts[2])
        system_cpu = float(parts[4])
        avg_util = user_cpu + system_cpu

        log.info(f"Collected average CPU utilization: {avg_util:.2f}%")
        return avg_util

    except (ValueError, IndexError) as e:
        log.error(f"Failed to parse CPU utilization from sar output: {e}")
        debug_info = "Failed to parse sar 'Average:' line. " f"Raw sar output:\n---\n{output}\n---"
        raise ExecutionError(debug_info)
    except ExecutionError:
        raise


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
            events_flags.append(f"-e {{{events_str}}}")

    command_parts = [
        "perf",
        "stat",
        target_flag,
        *events_flags,
    ]
    if interval is not None:
        command_parts.append(f"-I {interval}")
    command = " ".join(command_parts)

    log.info(f"Starting background perf stat: {command}")
    return run_in_background(command)


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
    output_file: str,
) -> Optional[subprocess.Popen]:
    """
    Starts `sar -A` in the background to collect all system activities.
    在后台启动 `sar -A` 以收集所有系统活动。
    """
    count = duration // interval
    if count <= 0:
        log.warning(f"Duration ({duration}) is less than interval ({interval}), skipping sar.")
        return None

    command = f"sar -A {interval} {count}"

    log.info(f"Starting background sar: {command}")
    try:
        env = os.environ.copy()
        env["LC_ALL"] = "C"
        proc = subprocess.Popen(
            shlex.split(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        return proc
    except FileNotFoundError:
        raise ExecutionError("Command not found: sar")


def stop_sar(proc: subprocess.Popen, output_file: str, duration: int) -> Optional[str]:
    """
    Waits for the sar process to finish, captures its output, and saves to file.
    等待 sar 进程结束，捕获其输出，并保存到文件。

    :param proc: The sar subprocess.
    :param output_file: File to save the output.
    :param duration: The duration sar was supposed to run for timeout calculation.
    """
    log.info(f"Waiting for sar (PID: {proc.pid}) to finish...")
    timeout = duration + 15
    try:
        stdout_data, stderr_data = proc.communicate(timeout=timeout)

        if proc.returncode != 0:
            log.error(f"sar process exited with error code {proc.returncode}" ". Stderr: {stderr_data}")

        with open(output_file, "w") as f:
            f.write(stdout_data)
        log.info(f"sar report saved to {output_file}")

        return stdout_data
    except subprocess.TimeoutExpired:
        log.warning("sar process did not terminate as expected. Killing it...")
        proc.kill()
        stdout_data, _ = proc.communicate()
        return stdout_data
