"""
健康检查命令模块

此模块实现healthcheck命令，用于收集系统的静态信息。
包括CPU、内存、磁盘、网络、内核参数等系统配置信息。
"""

import logging
import re
from pathlib import Path

import click
import yaml

from src.executor import ExecutionError, run_command

log = logging.getLogger(__name__)


# --- Helper Functions ---
def _read_proc_file(filepath: str) -> dict:
    """Safely reads a /proc-style file with key-value pairs."""
    data = {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    key, value = line.split(":", 1)
                    data[key.strip()] = value.strip()
    except Exception as e:
        log.warning(f"Error reading {filepath}: {e}")
    return data


def _parse_os_release(filepath: str) -> dict:
    """Parses /etc/os-release style files (key="value")."""
    data = {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    key, value = line.split("=", 1)
                    data[key.strip()] = value.strip().strip('"')
    except Exception as e:
        log.warning(f"Error reading {filepath}: {e}")
    return data


# --- Robust Data Collectors (v2.1) ---
def _collect_cpu_info() -> dict:
    """Collects CPU info directly from /proc/cpuinfo, reading the file only once."""
    processors = 0
    model_name = "N/A"
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("processor"):
                    processors += 1
                elif line.lower().startswith("model name") or line.lower().startswith("model"):
                    model_name = line.split(":", 1)[1].strip()
    except Exception as e:
        log.warning(f"Could not parse /proc/cpuinfo: {e}")
    return {"CPU(s)": processors, "Model name": model_name}


def _collect_memory_info() -> dict:
    """Collects Memory info directly from /proc/meminfo."""
    return _read_proc_file("/proc/meminfo")


def _collect_numa_info() -> dict:
    """Collects NUMA topology info from /sys/devices/system/node/."""
    try:
        node_base_path = Path("/sys/devices/system/node")
        if not node_base_path.is_dir():
            return {"status": "NUMA not supported or /sys/devices/system/node not found."}

        numa_topology = {}
        for node_path in sorted(node_base_path.glob("node[0-9]*")):
            node_name = node_path.name
            cpulist_path = node_path / "cpulist"
            if cpulist_path.exists():
                cpu_list_str = cpulist_path.read_text().strip()
                numa_topology[node_name] = cpu_list_str

        if not numa_topology:
            return {"status": "No NUMA nodes detected."}

        return {"numa_topology": numa_topology}
    except Exception as e:
        log.warning(f"Could not collect NUMA info: {e}")
        return {"error": str(e)}


def _collect_cpu_governor_info() -> dict:
    """Collects the CPU frequency scaling governor for each CPU."""
    governors = {}
    try:
        cpu_dirs = Path("/sys/devices/system/cpu").glob("cpu[0-9]*")
        for cpu_dir in cpu_dirs:
            gov_path = cpu_dir / "cpufreq/scaling_governor"
            if gov_path.exists():
                governors[cpu_dir.name] = gov_path.read_text().strip()
        unique_governors = set(governors.values())
        if not governors:
            return {"status": "Not available or not configured"}
        return {"unique_governors": list(unique_governors)}
    except Exception as e:
        log.warning(f"Could not read CPU governor info: {e}")
        return {"error": str(e)}


def _collect_io_scheduler_info() -> dict:
    """Collects the I/O scheduler for each block device."""
    schedulers = {}
    try:
        for device_path in Path("/sys/class/block").iterdir():
            scheduler_path = device_path / "queue/scheduler"
            if scheduler_path.exists():
                scheduler_line = scheduler_path.read_text().strip()
                active_scheduler_match = re.search(r"\[([\w-]+)\]", scheduler_line)
                if active_scheduler_match:
                    schedulers[device_path.name] = active_scheduler_match.group(1)
                else:
                    schedulers[device_path.name] = scheduler_line
        return schedulers
    except Exception as e:
        log.warning(f"Could not read I/O scheduler info: {e}")
        return {"error": str(e)}


def _collect_sysctl_info() -> dict:
    """Collects a unified set of critical kernel parameters via sysctl."""
    params = {}
    params_to_get = [
        "vm.swappiness",
        "kernel.pid_max",
        "net.core.somaxconn",
        "vm.dirty_ratio",
        "vm.dirty_background_ratio",
        "vm.dirty_bytes",
        "vm.dirty_background_bytes",
        "vm.overcommit_memory",
        "fs.file-max",
    ]
    try:
        sysctl_output = run_command(f"sysctl {' '.join(params_to_get)}")
        for line in sysctl_output.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                params[key.strip()] = value.strip()
    except ExecutionError:
        log.warning("Could not collect sysctl parameters.")
    return params


def _collect_disk_info_from_sys() -> dict:
    """
    从 /sys/class/block 收集块设备信息，构建 磁盘 -> 分区 的层级结构。
    """
    sys_block_path = Path("/sys/class/block")
    if not sys_block_path.exists():
        return {"error": "/sys/class/block not found."}

    block_devices = []

    # 1. 遍历所有块设备
    for device_path in sys_block_path.iterdir():
        dev_name = device_path.name

        # --- 过滤逻辑 ---
        # 排除 loop, ram 设备
        if dev_name.startswith(("loop", "ram")):
            continue

        # 排除分区 (Partition)
        # 在 /sys/class/block 下，分区也会作为顶级链接出现，但它们包含 'partition' 文件。
        # 我们只想处理“物理磁盘”或“逻辑卷根设备”，然后在它们内部找分区。
        if (device_path / "partition").exists():
            continue

        # --- 采集物理磁盘信息 ---
        try:
            size_sectors = int((device_path / "size").read_text().strip())
            size_bytes = size_sectors * 512

            disk_info = {
                "name": dev_name,
                "type": "disk",  # 默认为 disk，如果是 dm-x 可能会改
                "size_bytes": size_bytes,
                "model": "N/A",
                "vendor": "N/A",
                "rotational": "N/A",  # 0=SSD, 1=HDD
                "partitions": [],  # 准备挂载分区
            }

            # 采集额外属性
            if (device_path / "device/model").exists():
                disk_info["model"] = (device_path / "device/model").read_text().strip()
            if (device_path / "device/vendor").exists():
                disk_info["vendor"] = (device_path / "device/vendor").read_text().strip()
            if (device_path / "queue/rotational").exists():
                rot = (device_path / "queue/rotational").read_text().strip()
                disk_info["rotational"] = "HDD" if rot == "1" else "SSD"

            # 特殊处理 Device Mapper (dm-x)
            if dev_name.startswith("dm-"):
                disk_info["type"] = "lvm/dm"
                # dm 设备通常没有 model/vendor，尝试读取 dm/name
                if (device_path / "dm/name").exists():
                    disk_info["model"] = (device_path / "dm/name").read_text().strip()

            # --- 核心：扫描分区 (找儿子) ---
            # 在 sysfs 中，分区目录通常直接位于磁盘目录下，名字以磁盘名开头 (sda -> sda1)
            # 或者只是作为子目录存在。最稳健的方法是遍历子目录并检查 'partition' 文件。
            # 注意：device_path 是个软链接，resolve() 后才能看到真正的物理目录结构
            real_device_path = device_path.resolve()

            for sub_path in real_device_path.iterdir():
                # 只有当子目录包含 'partition' 文件时，才认为是分区
                if sub_path.is_dir() and (sub_path / "partition").exists():
                    try:
                        part_sectors = int((sub_path / "size").read_text().strip())
                        part_info = {"name": sub_path.name, "type": "partition", "size_bytes": part_sectors * 512}
                        disk_info["partitions"].append(part_info)
                    except (ValueError, IOError):
                        continue

            # 对分区按名称排序 (sda1, sda2...)
            disk_info["partitions"].sort(key=lambda x: x["name"])

            block_devices.append(disk_info)

        except (IOError, ValueError) as e:
            log.warning(f"Could not fully read info for device {dev_name}: {e}")

    # 对磁盘按名称排序
    block_devices.sort(key=lambda x: x["name"])

    return {"block_devices": block_devices}


def _parse_ip_addr(raw_output: str) -> dict:
    """Parses `ip addr` output into a structured dictionary."""
    interfaces = {}
    current_iface = None
    for line in raw_output.splitlines():
        if not line.strip():
            continue
        match = re.match(r"^\d+:\s+([\w@\.-]+):", line)
        if match:
            current_iface = match.group(1)
            interfaces[current_iface] = {"state": [], "mac": "N/A", "ipv4": [], "ipv6": []}
            if "<" in line and ">" in line:
                state_match = re.search(r"<([\w,]+)>", line)
                if state_match:
                    interfaces[current_iface]["state"] = state_match.group(1).split(",")
        elif current_iface:
            line_stripped = line.strip()
            if line_stripped.startswith("link/ether"):
                interfaces[current_iface]["mac"] = line_stripped.split()[1]
            elif line_stripped.startswith("inet "):
                interfaces[current_iface]["ipv4"].append(line_stripped.split()[1])
            elif line_stripped.startswith("inet6 "):
                interfaces[current_iface]["ipv6"].append(line_stripped.split()[1])
    return {"network_interfaces": interfaces}


def _collect_all_static_info() -> dict:
    """Master collector function for Healthcheck 2.0."""
    log.info("🚀 Starting Healthcheck 2.0: Interrogating kernel directly...")
    info = {
        "os_info": _parse_os_release("/etc/os-release"),
        "kernel_version": {"version": "N/A"},
        "cpu_info": _collect_cpu_info(),
        "numa_info": _collect_numa_info(),
        "cpu_governor": _collect_cpu_governor_info(),
        "memory_info": _collect_memory_info(),
        "disk_info": _collect_disk_info_from_sys(),
        "io_scheduler": _collect_io_scheduler_info(),
        "net_info": {"error": "Failed to run 'ip addr' command"},
        "kernel_parameters": _collect_sysctl_info(),
    }
    try:
        info["kernel_version"]["version"] = run_command("uname -r").strip()
    except ExecutionError as e:
        log.warning(f"Could not get kernel version: {e}")
    try:
        ip_out = run_command("ip addr")
        info["net_info"] = _parse_ip_addr(ip_out)
    except ExecutionError as e:
        log.warning(f"Could not collect network info: {e}")
    log.info("✅ System interrogation complete.")
    return info


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
    收集静态系统信息并保存到文件。

    收集系统的硬件和软件配置信息，包括操作系统、内核、
    CPU、内存、磁盘、网络等，并保存为YAML格式文件。
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
