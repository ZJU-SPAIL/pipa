"""
命令执行模块

此模块提供执行系统命令的功能，包括同步执行和后台执行。
处理命令的输出、错误和超时情况，并提供自定义异常类。
"""

import logging
import os
import shlex
import subprocess
from typing import Dict, Optional

# 为此模块配置一个简单的日志记录器
log = logging.getLogger(__name__)


class ExecutionError(Exception):
    """命令执行错误的自定义异常类。"""

    pass


class PerfPermissionError(ExecutionError):
    """当perf执行因内核权限设置失败时抛出的异常。"""

    pass


def run_command(command: str, timeout: Optional[int] = None, env: Optional[Dict[str, str]] = None) -> str:
    """
    执行一个shell命令并返回其标准输出。

    使用subprocess.run执行命令，设置环境变量LC_ALL=C以确保输出格式一致。
    如果命令执行失败，会抛出ExecutionError异常。

    参数:
        command: 要执行的命令字符串。
        timeout: 可选的超时时间（秒）。
        env: 可选的环境变量字典，用于覆盖默认环境。

    返回:
        命令的标准输出内容（去除首尾空白）。

    异常:
        ExecutionError: 如果命令未找到、执行失败或超时。
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
    在后台执行一个shell命令。

    使用subprocess.Popen启动后台进程，不等待完成。
    进程组设置为新会话，以便独立管理。

    参数:
        command: 要执行的命令字符串。

    返回:
        启动的subprocess.Popen对象。

    异常:
        ExecutionError: 如果命令未找到。
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
