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
    :raises ExecutionError: If sar command fails.
    """
    # sar -u [interval] [count]
    # We collect one more sample than needed to get the final "Average" line.
    # 我们比所需多采集一个样本，以获得最终的 "Average" 行。
    count = duration // interval
    command = f"sar -u {interval} {count}"

    # Define the environment we need
    # 定义我们需要的环境
    env = {"LC_ALL": "C"}

    output = ""

    try:
        output = run_command(command, env=env)

        lines = output.strip().splitlines()

        # Filter for the data lines (which contain numbers and "all")
        # 筛选出包含数字和 "all" 的数据行
        cpu_data_lines = [
            line.split()
            for line in lines
            if (
                len(line.split()) > 4
                and line.split()[1] == "all"
                and line.split()[0] != "Average:"
            )
        ]

        if not cpu_data_lines:
            raise ExecutionError("No valid CPU data lines found in sar output.")

        # Calculate the average from all data lines ourselves
        # 我们自己从所有数据行中计算平均值
        total_user = 0.0
        total_system = 0.0
        valid_lines = 0
        for parts in cpu_data_lines:
            # Example line: 11:25:01     all      2.35     0.00      1.73 ...
            # Parts:          [0]       [1]    [2]       [3]      [4]       [5]
            try:
                total_user += float(parts[2])
                total_system += float(parts[4])
                valid_lines += 1
            except (ValueError, IndexError):
                # Ignore lines that are not valid data (like the header)
                # 忽略无效的数据行（比如表头）
                continue

        if valid_lines == 0:
            raise ExecutionError("Could not parse any CPU data lines from sar output.")
        avg_util = (total_user + total_system) / valid_lines

        log.info(f"Collected average CPU utilization: {avg_util:.2f}%")
        return avg_util

    except ExecutionError:
        # Re-raise ExecutionError as-is (for test matching)
        raise
    except (ValueError, IndexError, ZeroDivisionError) as e:
        log.error(f"Failed to collect or parse CPU utilization: {e}")
        # Add the raw output to the error for better debugging
        # 在错误信息中加入原始输出，以便更好地调试
        debug_info = (
            f"Failed to determine CPU utilization. Raw sar output:\n---\n{output}\n---"
        )
        raise ExecutionError(debug_info)
