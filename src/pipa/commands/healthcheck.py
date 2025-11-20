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
    """Collects block device info directly from /sys for maximum robustness."""
    devices = []
    sys_block_path = Path("/sys/class/block")
    if not sys_block_path.exists():
        return {"error": "/sys/class/block not found."}
    for device_path in sys_block_path.iterdir():
        try:
            if (device_path / "partition").exists():
                continue

            size_sectors = int((device_path / "size").read_text().strip())
            size_bytes = size_sectors * 512

            device_info = {
                "name": device_path.name,
                "size_bytes": size_bytes,
                "type": "disk",
                "removable": "N/A",
                "model": "N/A",
            }

            if (device_path / "removable").exists():
                device_info["removable"] = (device_path / "removable").read_text().strip() == "1"
            if (device_path / "device/model").exists():
                device_info["model"] = (device_path / "device/model").read_text().strip()

            devices.append(device_info)
        except (IOError, ValueError, FileNotFoundError) as e:
            log.warning(f"Could not fully read info for device {device_path.name}: {e}")
    return {"block_devices": devices}


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
