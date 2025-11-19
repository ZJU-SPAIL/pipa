"""
性能数据收集模块

此模块负责收集系统和进程的性能数据，包括CPU、内存、网络、I/O等指标。
使用perf和sar工具来收集数据，并提供启动、停止和处理数据的功能。
"""

import logging
import os
import platform
import shlex
import signal
import subprocess
from pathlib import Path
from typing import Optional

from .executor import ExecutionError, PerfPermissionError, run_command

log = logging.getLogger(__name__)

# --- 内置事件集 ---

# x86_64架构（Intel/AMD）的通用事件集
X86_64_EVENT_SET = [
    ["cycles", "instructions"],
    ["cache-references", "cache-misses"],
    ["branch-instructions", "branch-misses"],
    ["L1-dcache-loads", "L1-dcache-load-misses"],
    ["LLC-loads", "LLC-load-misses"],
    ["dTLB-loads", "dTLB-load-misses"],
    ["iTLB-loads", "iTLB-load-misses"],
    ["page-faults", "context-switches", "cpu-migrations"],
]

# aarch64架构（ARM64）的精心选择的事件集
AARCH64_EVENT_SET = [
    # 基础事件 (cycles, instructions 其实 Metrics 也会带，但显式加上更保险，方便算 IPC)
    ["cpu-cycles", "instructions"],
    ["branch-misses"],
    ["l1d_cache", "l1d_cache_refill"],
    ["l2d_cache", "l2d_cache_refill"],
    ["ll_cache_rd", "ll_cache_miss_rd"],
    ["dTLB-load-misses", "iTLB-load-misses"],
    ["page-faults", "context-switches", "cpu-migrations"],
]


def start_perf_stat(
    target_pid: Optional[str],
    system_wide: bool,
    interval: Optional[int] = 1000,
    events_override_str: Optional[str] = None,
    metrics_list: Optional[list] = None,  # <--- 新增参数
) -> Optional[subprocess.Popen]:
    """
    启动perf stat以进程特定或系统范围模式运行，强制使用CSV格式。

    根据提供的参数启动perf stat进程，用于收集性能统计数据。
    支持自定义事件集或使用内置的架构特定事件集。

    参数:
        target_pid: 可选的目标进程ID。如果提供，将监控特定进程。
        system_wide: 是否以系统范围模式运行。如果为True，将监控所有CPU核心。
        interval: 采样间隔（毫秒），默认为1000ms。
        events_override_str: 可选的自定义事件字符串，覆盖默认事件集。
        metrics_list: 可选的perf metrics列表，用于TopDown分析。

    返回:
        启动的subprocess.Popen对象，如果启动失败则返回None。

    异常:
        ExecutionError: 如果perf命令未找到。
    """
    # 处理事件集：优先使用用户提供的自定义事件，否则根据架构选择内置事件集
    if events_override_str:
        log.info(f"Using expert-provided perf events: {events_override_str}")
        event_groups = [events_override_str.split(",")]
    else:
        # 自动检测主机架构并选择相应的事件集
        host_arch = platform.machine()
        log.info(f"Auto-detected host architecture: {host_arch}")
        if host_arch == "aarch64":
            log.info("Using built-in aarch64 event set.")
            event_groups = AARCH64_EVENT_SET
        else:
            log.info("Using built-in x86_64 event set as default.")
            event_groups = X86_64_EVENT_SET

    # 构建perf stat命令的基础部分
    command_parts = ["perf", "stat"]

    # === FIX: 强制开启 CSV 模式，分隔符为分号 ===
    command_parts.extend(["-x", ";"])

    # 根据模式添加相应的命令行参数
    if system_wide:
        log.info("Running perf stat in system-wide mode with per-core stats (-a -A).")
        # === FIX: 确保 -A 始终存在，这样解析器逻辑才统一 ===
        command_parts.extend(["-a", "-A"])  # -a: 系统范围，-A: 每核心统计
    elif target_pid:
        log.info(f"Running perf stat in process-specific mode for PID(s): {target_pid}")
        command_parts.extend(["-p", target_pid])  # -p: 指定进程ID
    else:
        raise ValueError("Either target_pid or system_wide must be specified.")

    # 1. 先添加 -M Metrics (让 perf 优先处理指标)
    if metrics_list:
        log.info(f"Adding perf metrics: {metrics_list}")
        command_parts.append("-M")
        command_parts.append(",".join(metrics_list))

    # 2. 再添加基础 -e 事件 (作为补充)
    for group in event_groups:
        if group:
            command_parts.append("-e")
            command_parts.append(",".join(group))

    # 添加采样间隔参数
    command_parts.extend(
        [
            "-I",
            str(interval or 1000),
        ]
    )

    log.info(f"Starting background perf stat: {' '.join(command_parts)}")
    try:
        # 启动后台进程，设置进程组以便独立管理
        proc = subprocess.Popen(
            command_parts,
            shell=False,
            stdout=subprocess.DEVNULL,  # 丢弃标准输出
            stderr=subprocess.PIPE,  # 捕获标准错误（包含性能数据）
            text=True,
            preexec_fn=os.setsid,  # 创建新进程组
        )
        return proc
    except FileNotFoundError:
        raise ExecutionError("Command not found: perf")


# 修改 stop_perf_stat 函数的签名和实现
def stop_perf_stat(proc: subprocess.Popen, output_file: str, timeout: int) -> Optional[str]:
    """
    停止perf stat进程，捕获其stderr输出，写入文件，并返回内容。

    向perf stat进程发送SIGINT信号，等待其完成，捕获输出，
    并将结果保存到指定文件。如果遇到权限问题，会抛出PerfPermissionError。

    参数:
        proc: 要停止的perf stat进程对象。
        output_file: 输出文件的路径。
        timeout: 等待进程完成的超时时间（秒）。

    返回:
        捕获的stderr输出内容，如果进程被杀死则返回"Process killed, no output captured."。

    异常:
        PerfPermissionError: 如果内核的perf_event_paranoid设置过于严格。
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
    在后台启动sar -A，将二进制数据写入输出文件。

    启动sar工具以收集系统活动报告，使用二进制模式输出，
    这比捕获stdout更健壮。收集的数据包括CPU、网络、I/O、内存等指标。

    参数:
        duration: 收集数据的总持续时间（秒）。
        interval: 采样间隔（秒）。
        output_bin_file: 二进制输出文件的路径。

    返回:
        启动的subprocess.Popen对象，如果duration小于interval则返回None。

    异常:
        ExecutionError: 如果sar命令未找到。
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
    level_dir: Path,  # <- 新增参数
    timeout: int,
) -> None:
    """
    等待sar进程完成，然后使用sadf将其二进制输出转换为多个分类的CSV文件。

    等待sar进程结束，然后使用sadf工具将二进制数据转换为CSV格式，
    生成多个CSV文件，每个文件对应不同的系统指标类别。

    参数:
        proc: 要等待的sar进程对象。
        output_bin_file: sar生成的二进制输出文件路径。
        level_dir: 保存CSV文件的目录路径。
        timeout: 等待进程完成的超时时间（秒）。
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

    log.info("Sar process finished. Converting binary output to multiple CSVs...")

    sar_metric_maps = {
        "cpu": "-d -- -P ALL",
        "network": "-d -- -n DEV",
        "io": "-d -- -b",
        "memory": "-d -- -r",
        "paging": "-d -- -B",
        "load": "-d -- -q",
        "cswch": "-d -- -w",
    }

    for name, options in sar_metric_maps.items():
        output_csv_file = level_dir / f"sar_{name}.csv"
        sadf_command = f"sadf {options} -- {shlex.quote(output_bin_file)}"
        try:
            csv_output = run_command(sadf_command)
            if csv_output:
                with open(output_csv_file, "w") as f:
                    f.write(csv_output)
                log.info(f"Successfully converted sar data to CSV: {output_csv_file.name}")
            else:
                log.warning(f"sadf command for '{name}' produced no output.")
        except (ExecutionError, FileNotFoundError) as e:
            log.error(f"Failed to convert sar '{name}' data to CSV using sadf: {e}")
        except IOError as e:
            log.error(f"Failed to write sar CSV file to {output_csv_file}: {e}")


def start_perf_record(
    target_pid: str,
    output_file: str,
    freq: Optional[int] = 99,
) -> Optional[subprocess.Popen]:
    """
    在后台启动perf record以生成火焰图。

    启动perf record进程来收集调用栈样本，用于生成性能火焰图。
    使用指定的频率采样目标进程的性能数据。

    参数:
        target_pid: 要监控的目标进程ID。
        output_file: 输出文件的路径，用于保存perf数据。
        freq: 采样频率（Hz），默认为99。

    返回:
        启动的subprocess.Popen对象。

    异常:
        ExecutionError: 如果perf命令未找到。
    """
    command = [
        "perf",
        "record",
        "-p",
        target_pid,
        "-o",
        output_file,
        "-F",
        str(freq or 99),
        "-g",
        "--",
    ]

    log.info(f"Starting background perf record: {' '.join(command)}")
    try:
        proc = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid,
        )
        return proc
    except FileNotFoundError:
        raise ExecutionError("Command not found: perf")


def stop_perf_record(proc: subprocess.Popen, timeout: int) -> None:
    """
    优雅地停止正在运行的perf record进程。

    向perf record进程发送SIGINT信号，等待其完成写入数据。
    如果进程没有响应，将强制杀死它。

    参数:
        proc: 要停止的perf record进程对象。
        timeout: 等待进程完成的超时时间（秒）。
    """
    log.info(f"Sending SIGINT to perf record process (PID: {proc.pid})...")
    proc.send_signal(signal.SIGINT)

    log.info("Waiting for perf record to finish writing data...")
    try:
        _, stderr_output = proc.communicate(timeout=timeout)
        if proc.returncode != 0:
            log.warning(f"perf record exited with code {proc.returncode}. Stderr: {stderr_output}")
        else:
            log.info("perf record process stopped successfully.")
    except subprocess.TimeoutExpired:
        log.warning("perf record process did not respond to SIGINT. Killing it...")
        proc.kill()
        proc.communicate()
