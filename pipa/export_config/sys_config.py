from pipa.export_config.utils import run_command_and_write_to_file, copy_file


def get_dmidecode():
    return run_command_and_write_to_file("sudo dmidecode", "dmidecode.txt")


def get_lspci():
    return run_command_and_write_to_file("lspci", "lspci.txt")


def get_lsusb():
    return run_command_and_write_to_file("lsusb", "lsusb.txt")


def get_disk_usage():
    return run_command_and_write_to_file("df -h", "disk_usage.txt")


def get_interrupt_info():
    return copy_file("/proc/interrupts")


def get_meminfo():
    return copy_file("/proc/meminfo")


def get_version():
    return copy_file("/proc/version")


def get_all_sys_config():
    get_dmidecode()
    get_lspci()
    get_lsusb()
    get_disk_usage()
    get_interrupt_info()
    get_meminfo()
    get_version()


if __name__ == "__main__":
    get_all_sys_config()
