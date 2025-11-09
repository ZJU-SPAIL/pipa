import logging
import os
import platform
import shlex
import signal
import subprocess
from typing import Optional

from .executor import (
    ExecutionError,
    PerfPermissionError,
    run_command,
)

log = logging.getLogger(__name__)
# --- Built-in Event Sets ---

# A robust, general-purpose event set for x86_64 architectures (Intel/AMD)
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

# A carefully selected event set for aarch64 architectures (ARM64)
AARCH64_EVENT_SET = [
    ["cpu-cycles", "instructions"],
    ["branch-instructions", "branch-misses"],
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
) -> Optional[subprocess.Popen]:
    """
    Starts perf stat in either process-specific or system-wide mode.
    """
    if events_override_str:
        log.info(f"Using expert-provided perf events: {events_override_str}")
        event_groups = [events_override_str.split(",")]
    else:
        host_arch = platform.machine()
        log.info(f"Auto-detected host architecture: {host_arch}")
        if host_arch == "aarch64":
            log.info("Using built-in aarch64 event set.")
            event_groups = AARCH64_EVENT_SET
        else:
            log.info("Using built-in x86_64 event set as default.")
            event_groups = X86_64_EVENT_SET

    command_parts = ["perf", "stat"]

    if system_wide:
        log.info("Running perf stat in system-wide mode with per-core stats (-a -A).")
        command_parts.extend(["-a", "-A"])
    elif target_pid:
        log.info(f"Running perf stat in process-specific mode for PID(s): {target_pid}")
        command_parts.extend(["-p", target_pid])
    else:
        raise ValueError("Either target_pid or system_wide must be specified.")

    for group in event_groups:
        if group:
            command_parts.append("-e")
            command_parts.append(",".join(group))

    command_parts.extend(
        [
            "-I",
            str(interval or 1000),
        ]
    )

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
    sadf_command = f"sadf -P ALL -d -- {shlex.quote(output_bin_file)}"
    try:
        csv_output = run_command(sadf_command)
        with open(output_csv_file, "w") as f:
            f.write(csv_output)
        log.info(f"Successfully converted sar data to CSV: {output_csv_file}")
    except (ExecutionError, FileNotFoundError) as e:
        log.error(f"Failed to convert sar data to CSV using sadf: {e}")
    except IOError as e:
        log.error(f"Failed to write sar CSV file to {output_csv_file}: {e}")


def start_perf_record(
    target_pid: str,
    output_file: str,
    freq: Optional[int] = 99,
) -> Optional[subprocess.Popen]:
    """
    Starts `perf record` in the background for flame graph generation.
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
    Stops the running `perf record` process gracefully.
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
