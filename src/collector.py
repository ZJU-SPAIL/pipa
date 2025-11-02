# src/collector.py

import logging
from .executor import run_command, ExecutionError

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
