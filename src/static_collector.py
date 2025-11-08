import logging
from typing import Any, Dict, List, Optional

from .executor import ExecutionError, run_command

log = logging.getLogger(__name__)


def _get_info(command: str, description: str) -> str:
    """Helper to run a command and return its output or a failure message."""
    try:
        return run_command(command)
    except ExecutionError as e:
        log.warning(f"Failed to collect {description}: {e}")
        return f"Error collecting {description}"
    except FileNotFoundError:
        # 捕捉命令本身找不到的情况 (例如 numactl)
        log.warning(f"Command not found for {description}: {command}")
        return f"Error collecting {description}: Command not found"


def _handle_error(raw_output: str, description: str) -> Optional[Dict[str, str]]:
    """检查 _get_info 的输出是否是错误信息，如果是则返回一个结构化的错误字典。"""
    if raw_output.startswith("Error collecting"):
        return {"error": raw_output, "source": description}
    return None  # 返回 None 表示没有错误


# --- 解析函数 (Parsers) ---


def _parse_key_value_lines(raw_output: str, separator="=") -> Dict[str, str]:
    """通用解析器：用于解析 Key=Value 或 Key: Value 格式的行 (如 os-release)。"""
    info = {}
    for line in raw_output.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if separator in line:
            key, value = line.split(separator, 1)
            # 移除引号
            value = value.strip().strip('"').strip("'")
            info[key.strip()] = value
    return info


def _parse_os_info(raw_output: str) -> dict:
    """解析 /etc/os-release 的输出。"""
    return _parse_key_value_lines(raw_output)


def _parse_kernel_info(raw_output: str) -> dict:
    """解析 uname -a 的输出。"""
    # uname -a 输出是一个长字符串，我们只取整体
    return {"Full_Kernel_Info": raw_output}


def _parse_lscpu_output(raw_output: str) -> dict:
    """解析 lscpu 的输出。"""
    info = {}
    for line in raw_output.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()

            # 尝试将数字转换为整数
            try:
                if value.isdigit():
                    value = int(value)
                # 尝试将 KB/MB/GB 单位的值转换为浮点数（可选，这里保持原始值/单位分开存储）
            except ValueError:
                pass

            # 格式化键名
            if key == "CPU(s)":
                info["CPUs_Count"] = value
            elif key == "Model name":
                info["Model_Name"] = value
            else:
                info[key.replace(" ", "_")] = value
    return info


def _parse_mem_info(raw_output: str) -> Dict[str, Any]:
    """
    解析 /proc/meminfo 的输出，只包含 OS 运行时的内存统计信息。
    """
    info = {}
    # /proc/meminfo 是 Key: Value，单位通常是 kB
    for line in raw_output.splitlines():
        if ":" in line:
            key, value_unit = line.split(":", 1)
            key = key.strip()
            value_unit = value_unit.strip().split()

            # 将值和单位分开，方便后续处理
            if len(value_unit) == 2:
                value, unit = value_unit
                try:
                    value = int(value)
                except ValueError:
                    pass
                # 存储为 Key_UNIT 格式，例如 MemTotal_KB
                info[f"{key}_{unit.upper()}"] = value
            else:
                # 针对没有单位的行（极少）
                info[key] = value_unit[0] if value_unit else ""

    return info


def _parse_disk_info(df_output: str, lsblk_output: str) -> dict:
    df_info = []
    lines = df_output.splitlines()
    if len(lines) > 1:
        headers = lines[0].split()  # 文件系统、大小、已用、可用、用量%、挂载点

        # 修正：确保头部有 6 个元素
        if len(headers) < 6:
            # 如果 headers 不足 6 个，可能头部被错误解析，跳过解析
            pass
        else:
            # 确保只使用 df -h 的标准 6 个头部
            headers = headers[:6]

            for line in lines[1:]:
                # 使用 split(maxsplit=5) 来保证最多只分割前 5 个列，剩下的都归于第 6 列 (Mounted on)
                values = line.split(maxsplit=5)

                # 检查是否成功分割成 6 个部分
                if len(values) == 6:
                    df_info.append(dict(zip(headers, values)))

    # ... lsblk 解析 (保留不变) ...
    # lsblk_list = lsblk_output.strip().splitlines()

    return {
        "Filesystem_Usage": df_info,
        "Block_Devices_Raw": lsblk_output.strip().splitlines(),
    }


def _parse_nmcli_output(raw_output: str) -> list:
    """解析 nmcli device show 的输出。"""
    devices = []
    current_device = {}

    for line in raw_output.splitlines():
        line = line.strip()

        if not line:
            if current_device:
                devices.append(current_device)
                current_device = {}
            continue

        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().replace(" ", "_").upper()
            value = value.strip()

            # 使用更简洁的键名
            if "." in key:
                key = key.split(".", 1)[1]

            # 移除空值
            if value:
                current_device[key] = value

    if current_device:
        devices.append(current_device)

    return devices


# --- 收集函数 (Collectors) ---


def get_os_info() -> Dict[str, str]:
    """Gets OS release information and returns it as a structured dictionary."""
    raw_output = _get_info("cat /etc/os-release", "OS info")
    if error := _handle_error(raw_output, "OS info"):
        return error
    return _parse_os_info(raw_output)


def get_kernel_info() -> Dict[str, str]:
    """Get kernel version information.

    Returns it as a structured dictionary.
    """
    raw_output = _get_info("uname -a", "Kernel info")
    if error := _handle_error(raw_output, "Kernel info"):
        return error
    return _parse_kernel_info(raw_output)


def get_cpu_info() -> Dict[str, Any]:
    """Get detailed CPU information.

    Returns it as a structured dictionary.
    """
    raw_output = _get_info("lscpu", "CPU info")
    if error := _handle_error(raw_output, "CPU info"):
        return error
    return _parse_lscpu_output(raw_output)


def get_mem_info() -> Dict[str, Any]:
    """
    Gets OS runtime memory statistics from /proc/meminfo.
    """
    # 1. OS 运行时的内存统计信息 (/proc/meminfo)
    mem_output = _get_info("cat /proc/meminfo", "OS Memory Stats")

    if error := _handle_error(mem_output, "OS Memory Stats"):
        # 如果收集失败，直接返回错误字典
        return error
    # 如果收集成功，解析数据
    return _parse_mem_info(mem_output)


def get_disk_info() -> Dict[str, Any]:
    """Get disk space and layout information.

    Returns a structured dictionary.
    """
    df_output = _get_info("df -h", "Disk Filesystem info")
    lsblk_output = _get_info("lsblk", "Disk Block Device info")

    # 检查是否有错误，如果两者都有错误，返回整体错误
    if df_output.startswith("Error collecting") and lsblk_output.startswith("Error collecting"):
        return {"error": "Both df -h and lsblk failed to collect info."}

    return _parse_disk_info(df_output, lsblk_output)


def get_network_info() -> List[Dict[str, str]]:
    """Get network interface information via nmcli.

    Returns a list of structured dictionaries.
    """
    raw_output = _get_info("nmcli device show", "Network info (nmcli)")
    # _handle_error 返回 dict[str, str] 或 None
    if error := _handle_error(raw_output, "Network info (nmcli)"):
        return [error]
    return _parse_nmcli_output(raw_output)


def get_numa_info() -> Dict[str, Any]:
    """Gets NUMA node information and returns it as a structured dictionary."""
    try:
        raw_output = run_command("numactl --hardware")
        # numactl 输出也是 Key: Value 格式，这里使用通用解析器
        parsed_info = _parse_key_value_lines(raw_output, separator=":")
        return parsed_info
    except ExecutionError as e:
        log.warning(
            "'numactl' not found or failed. NUMA info unavailable: %s",
            e,
        )
        return {"error": ("'numactl' command failed or not found. " "Please install 'numactl'.")}


# --- 主收集函数 ---


def collect_all_static_info() -> dict:
    """Collect all static system information.

    Returns a nested dictionary ready for JSON serialization.

    收集所有静态系统信息，并以字典形式返回，可直接用于JSON序列化。
    """
    log.info("Collecting static system information...")
    info = {
        "os_info": get_os_info(),
        "kernel_info": get_kernel_info(),
        "cpu_info": get_cpu_info(),
        "mem_info": get_mem_info(),  # 仅收集 /proc/meminfo
        "disk_info": get_disk_info(),
        "network_info": get_network_info(),
        "numa_info": get_numa_info(),
    }
    log.info("Static information collected successfully.")
    return info
