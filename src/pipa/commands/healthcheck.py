import logging
from pathlib import Path
from typing import Any, Dict, Optional

import click
import yaml

# --- 核心修改: 导入路径已根据新结构进行验证 ---
from src.executor import ExecutionError, run_command

log = logging.getLogger(__name__)


# --- 核心修改: 所有来自 static_collector.py 的逻辑被移入此文件并设为私有 ---
def _get_info(command: str, description: str) -> str:
    """Helper to run a command and return its output or a failure message."""
    try:
        return run_command(command)
    except ExecutionError as e:
        log.warning(f"Failed to collect {description}: {e}")
        return f"Error collecting {description}"
    except FileNotFoundError:
        log.warning(f"Command not found for {description}: {command}")
        return f"Error collecting {description}: Command not found"


def _handle_error(raw_output: str, description: str) -> Optional[Dict[str, str]]:
    """检查 _get_info 的输出是否是错误信息。"""
    if raw_output.startswith("Error collecting"):
        return {"error": raw_output, "source": description}
    return None


def _parse_key_value_lines(raw_output: str, separator="=") -> Dict[str, str]:
    info = {}
    for line in raw_output.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if separator in line:
            key, value = line.split(separator, 1)
            value = value.strip().strip('"').strip("'")
            info[key.strip()] = value
    return info


def _parse_os_info(raw_output: str) -> dict:
    return _parse_key_value_lines(raw_output)


def _parse_kernel_info(raw_output: str) -> dict:
    return {"Full_Kernel_Info": raw_output}


def _parse_lscpu_output(raw_output: str) -> dict:
    info = {}
    for line in raw_output.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().replace(" ", "_")
            value = value.strip()
            if key == "CPU(s)":
                info["CPUs_Count"] = int(value)
            elif key == "Model_name":
                info["Model_Name"] = value
            else:
                info[key] = value
    return info


def _parse_numa_info(raw_output: str) -> dict:
    info = {}
    for line in raw_output.splitlines():
        line = line.strip()
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().replace(" ", "_")
            value = value.strip()
            info[key] = value
    return info


def _get_os_info() -> Dict[str, str]:
    raw_output = _get_info("cat /etc/os-release", "OS info")
    return _handle_error(raw_output, "OS info") or _parse_os_info(raw_output)


def _get_kernel_info() -> Dict[str, str]:
    raw_output = _get_info("uname -a", "Kernel info")
    return _handle_error(raw_output, "Kernel info") or _parse_kernel_info(raw_output)


def _get_cpu_info() -> Dict[str, Any]:
    raw_output = _get_info("lscpu", "CPU info")
    return _handle_error(raw_output, "CPU info") or _parse_lscpu_output(raw_output)


def _get_numa_info() -> Dict[str, Any]:
    raw_output = _get_info("numactl --hardware", "NUMA info")
    return _handle_error(raw_output, "NUMA info") or _parse_numa_info(raw_output)


def _collect_all_static_info() -> dict:
    """Collect all static system information."""
    log.info("Collecting static system information...")
    info = {
        "os_info": _get_os_info(),
        "kernel_info": _get_kernel_info(),
        "cpu_info": _get_cpu_info(),
        "numa_info": _get_numa_info(),
    }
    log.info("Static information collected successfully.")
    return info


# --- 核心修改: CLI 定义部分保持不变，但现在调用的是本地私有函数 ---
@click.command()
@click.option(
    "--output",
    "output_path_str",
    required=False,
    type=click.Path(writable=True, dir_okay=False, resolve_path=True),
    default="pipa_static_info.yaml",
    help="Path to save the static system information YAML file.",
)
def healthcheck(output_path_str: str):
    """
    Collects static system information and saves it to a file.
    """
    output_path = Path(output_path_str)
    try:
        click.echo("🚀 Collecting static system information...")
        static_info = _collect_all_static_info()

        with open(output_path, "w") as f:
            yaml.dump(static_info, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        click.secho(f"✅ Static information successfully saved to: {output_path}", fg="green")

    except Exception as e:
        click.secho(f"❌ An error occurred during health check: {e}", fg="red")
        raise click.Abort()
