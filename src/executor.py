import logging
import os
import shlex
import subprocess
from typing import Dict, Optional

# Configure a simple logger for this module
# 为此模块配置一个简单的日志记录器
log = logging.getLogger(__name__)


class ExecutionError(Exception):
    """Custom exception for command execution errors."""

    pass


class PerfPermissionError(ExecutionError):
    """Raised when perf execution fails due to kernel permission settings."""

    pass


def run_command(command: str, timeout: Optional[int] = None, env: Optional[Dict[str, str]] = None) -> str:
    """
    Executes a shell command and returns its stdout.
    执行一个 shell 命令并返回其标准输出。

    :param command: The command string to execute.
    :param timeout: Optional timeout in seconds.
    :param env: Optional environment variables to set for the command.
    :return: The stdout from the command.
    :raises ExecutionError: If the command returns a non-zero exit code.
    """
    log.info(f"Executing command: {command}")

    final_env = os.environ.copy()
    final_env["LC_ALL"] = "C"
    if env:
        final_env.update(env)

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
            env=final_env,
            shell=True,
        )
        log.debug(f"Command stdout:\n{result.stdout}")
        return result.stdout.strip()
    except FileNotFoundError:
        raise ExecutionError(f"Command not found: {shlex.split(command)[0]}")
    except subprocess.CalledProcessError as e:
        error_message = f"Command '{command}' failed with exit code {e.returncode}.\n"
        error_message += f"Stderr:\n{e.stderr.strip()}"
        log.error(error_message)
        raise ExecutionError(error_message)
    except subprocess.TimeoutExpired as e:
        error_message = f"Command '{e.cmd}' timed out after {e.timeout} seconds."
        log.error(error_message)
        raise ExecutionError(error_message)


# 在 run_in_background() 函数中，找到 subprocess.Popen 的调用
#
# 将其修改为：
def run_in_background(command: str) -> subprocess.Popen:
    """
    Executes a shell command in the background.
    在后台执行一个 shell 命令。
    """
    log.info(f"Executing background command: {command}")
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid,
        )
        return process
    except FileNotFoundError:
        raise ExecutionError(f"Command not found via shell: {command}")
