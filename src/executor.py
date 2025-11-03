import subprocess
import shlex
import logging
import os
from typing import Optional, Dict

# Configure a simple logger for this module
# 为此模块配置一个简单的日志记录器
log = logging.getLogger(__name__)


class ExecutionError(Exception):
    """Custom exception for command execution errors."""

    pass


def run_command(
    command: str, timeout: Optional[int] = None, env: Optional[Dict[str, str]] = None
) -> str:
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

    # Create a copy of the current environment and update it
    # 创建当前环境的副本并更新它
    final_env = os.environ.copy()
    if env:
        final_env.update(env)

    try:
        # shlex.split handles shell-like quoting correctly
        # shlex.split 能正确处理类似 shell 的引号
        result = subprocess.run(
            shlex.split(command),
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
            env=final_env,
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


def run_in_background(command: str) -> subprocess.Popen:
    """
    Executes a shell command in the background.
    在后台执行一个 shell 命令。

    :param command: The command string to execute.
    :return: A Popen object representing the running process.
    :raises ExecutionError: If the command fails to start.
    """
    log.info(f"Executing background command: {command}")
    try:
        # We don't capture output here as it's a background process
        # 我们在这里不捕获输出，因为它是一个后台进程
        process = subprocess.Popen(
            shlex.split(command),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        return process
    except FileNotFoundError:
        raise ExecutionError(f"Command not found: {shlex.split(command)[0]}")
