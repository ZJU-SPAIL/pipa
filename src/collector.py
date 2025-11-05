# src/collector.py

import logging
import subprocess
from typing import Optional
from .executor import run_command, ExecutionError
import signal
import time
from .executor import run_in_background

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
    # sar -u [interval] [count]
    # We collect 'duration' samples at 'interval' second intervals.
    # 我们以 'interval' 秒为间隔，收集 'duration' 个样本。
    count = duration // interval
    command = f"sar -u {interval} {count}"

    # Define the environment we need
    # 定义我们需要的环境
    env = {"LC_ALL": "C"}

    output = ""

    try:
        output = run_command(command, env=env)
        lines = output.strip().splitlines()

        # Find the "Average:" line, which contains the final summary.
        # 寻找包含最终摘要的 "Average:" 行。
        avg_line = None
        for line in reversed(lines):
            if line.strip().startswith("Average:"):
                avg_line = line
                break

        if not avg_line:
            raise ExecutionError("Could not find 'Average:' line in sar output.")

        log.debug(f"Line being parsed is: '{avg_line.strip()}'")

        parts = avg_line.split()
        # Expected format: Average: all %user %nice %system ...
        # parts index:      0        1    2     3     4
        if len(parts) < 5 or parts[1] != "all":
            raise ExecutionError("Unexpected format for 'Average:' line in sar output.")

        user_cpu = float(parts[2])
        system_cpu = float(parts[4])
        avg_util = user_cpu + system_cpu

        log.info(f"Collected average CPU utilization: {avg_util:.2f}%")
        return avg_util

    except (ValueError, IndexError) as e:
        log.error(f"Failed to parse CPU utilization from sar output: {e}")
        debug_info = (
            "Failed to parse sar 'Average:' line. "
            f"Raw sar output:\n---\n{output}\n---"
        )
        raise ExecutionError(debug_info)
    except ExecutionError:
        # Re-raise ExecutionError to propagate command failures
        # 重新抛出 ExecutionError 以传递命令失败信息
        raise


def collect_perf_stat(
    duration: int,
    output_file: str,
    mode: str = "pid",
    target_pid: Optional[int] = None,
    target_cpus: Optional[str] = None,
    event_groups: Optional[list[list[str]]] = None,
) -> None:
    """
    Collects performance counters using perf stat with advanced options.
    使用 perf stat 的高级选项收集性能计数器。

    :param duration: The total duration to monitor in seconds.
    :param output_file: The file to save the perf stat report.
    :param mode: The collection mode: "pid", "cpu", or "system".
    :param target_pid: The process ID to monitor (for "pid" mode).
    :param target_cpus: A string of CPUs to monitor, e.g., "0,2-4" (for "cpu" mode).
    :param event_groups: A list of event groups,
    e.g., [["cycles", "ins"], ["branches"]].
    :raises ExecutionError: If the perf command fails.
    :raises ValueError: If parameters are invalid for the selected mode.
    """
    if not event_groups:
        log.warning("No perf event groups specified. Skipping perf stat.")
        return

    # --- 1. 构建 target 参数 (使用字典派发) ---
    target_flag_builders = {
        "pid": lambda: f"-p {target_pid}" if target_pid else None,
        "cpu": lambda: f"-C {target_cpus}" if target_cpus else None,
        "system": lambda: "-a",
    }

    if mode not in target_flag_builders:
        raise ValueError(f"Invalid perf stat mode: {mode}")

    target_flag = target_flag_builders[mode]()
    if not target_flag:
        if mode == "pid":
            raise ValueError("target_pid parameter is required for 'pid' mode.")
        elif mode == "cpu":
            raise ValueError("target_cpus parameter is required for 'cpu' mode.")
        else:
            raise ValueError(f"target_{mode} parameter is required for '{mode}' mode.")

    # --- 2. 构建 events 参数 (支持分组) ---
    events_flags = []
    for group in event_groups:
        if group:
            events_str = ",".join(group)
            events_flags.append(f"-e {{{events_str}}}")

    # --- 3. 构建最终命令 ---
    if mode in ["pid", "cpu"]:
        command_parts = [
            "perf",
            "stat",
            target_flag,
            "-o",
            output_file,
            "--append",
            *events_flags,
        ]
        command = " ".join(command_parts)

        log.info(f"Executing background perf stat: {command} for {duration}s")
        perf_proc = run_in_background(command)
        try:
            time.sleep(duration)
        finally:
            if perf_proc.poll() is None:
                # SIGINT tells perf to print the report before exiting
                perf_proc.send_signal(signal.SIGINT)
                try:
                    perf_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    perf_proc.kill()
                    perf_proc.wait()
        log.info(f"perf stat report successfully saved to {output_file}")

    elif mode == "system":
        command_parts = [
            "perf",
            "stat",
            target_flag,
            "-o",
            output_file,
            "--append",
            *events_flags,
            "--",
            "sleep",
            str(duration),
        ]
        command = " ".join(command_parts)
        log.info(f"Executing perf stat with subcommand: {command}")
        try:
            run_command(command)
            log.info(f"perf stat report successfully saved to {output_file}")
        except ExecutionError as e:
            log.error(f"perf stat collection failed. Error: {e}")
            raise
