#!/bin/bash
# Export system configuration information
# Usage: ./export-configuration.sh [destination]
# Default destination is ./data/config
# Requires root privileges to run dmidecode and some other commands
# Author: Bernard Jiang, SPAIL, ZJU, 2024

# Check if the user has provided the --help option
if [[ "$1" == "--help" ]]; then
    echo "Usage: ./export-configuration.sh [destination]"
    echo "Default destination is ./data/config"
    echo "The script collects information about the system and writes it to a directory."
    echo "The directory is specified as the first argument to the script."
    echo "If no argument is provided, the script will write the data to the ./data/config directory."
    echo "The script uses various Linux commands to collect information about the system."
    echo "The commands used are:"
    echo "dmidecode"
    echo "lspci"
    echo "lsusb"
    echo "lsblk"
    echo "lshw"
    echo "lscpu"
    echo "lsmod"
    echo "lsinitrd"
    echo "ip"
    echo "df"
    echo "cp"
    exit 0
fi

DST="${1:-./data/config}"
if [[ $(id -u) -eq 0 ]]; then
    # User is root, run dmidecode directly
    dmidecode >/$DST/dmidecode.txt
else
    echo "You need to be root to run dmidecode, skipping..."
fi

if command -v lspci &>/dev/null; then
    lspci >"$DST/pci_devices.txt"
    echo "PCI devices exported to $DST/pci_devices.txt"
fi

if command -v lsusb &>/dev/null; then
    lsusb >"$DST/usb_devices.txt"
    echo "USB devices exported to $DST/usb_devices.txt"
fi

if command -v lsblk &>/dev/null; then
    lsblk >"$DST/block_devices.txt"
    echo "Block devices exported to $DST/block_devices.txt"
fi

if command -v lshw &>/dev/null; then
    lshw >"$DST/hardware.txt"
    echo "Hardware information exported to $DST/hardware.txt"
fi

if command -v lscpu &>/dev/null; then
    lscpu >"$DST/cpu.txt"
    echo "CPU information exported to $DST/cpu.txt"
    lscpu -a --extended >"$DST/cpu-extended.txt"
    echo "Extended CPU information exported to $DST/cpu-extended.txt"
fi

if command -v lsmod &>/dev/null; then
    lsmod >"$DST/modules.txt"
    echo "Kernel modules exported to $DST/modules.txt"
fi

if command -v lsinitrd &>/dev/null; then
    lsinitrd >"$DST/initrd.txt"
    echo "Initrd information exported to $DST/initrd.txt"
fi

if command -v ip &>/dev/null; then
    ip addr >"$DST/ip.txt"
    echo "IP information exported to $DST/ip.txt"
fi

df -h >"$DST/disk_usage.txt"
echo "Disk usage exported to $DST/disk_usage.txt"

cp /proc/meminfo "$DST/meminfo.txt"
echo "Memory information exported to $DST/meminfo.txt"

cp /proc/cpuinfo "$DST/cpuinfo.txt"
echo "CPU information exported to $DST/cpuinfo.txt"

perf list > "$DST/perf-list.txt"
echo "Perf list exported to $DST/perf-list.txt"

echo "Configuration exported to $DST"
