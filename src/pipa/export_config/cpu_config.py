from pipa.common.cmd import run_command
from pipa.export_config.utils import write_string_to_file, copy_file
import psutil


def get_lscpu_info():
    result = "{}\n\n\n{}".format(
        run_command("lscpu", log=True), run_command("lscpu -a --extended", log=True)
    )
    return write_string_to_file(result, "cpu_info.txt")


def get_cpuinfo():
    return copy_file("/proc/cpuinfo")


def get_all_cpu_config():
    get_lscpu_info()
    get_cpuinfo()


def get_cpu_cores():
    cpu_list = [
        l
        for l in run_command("lscpu -p=cpu", log=False).split("\n")
        if not l.startswith("#")
    ]
    return [int(x) for x in cpu_list]


NB_PHYSICAL_CORES = psutil.cpu_count(logical=False)

if __name__ == "__main__":
    get_all_cpu_config()
