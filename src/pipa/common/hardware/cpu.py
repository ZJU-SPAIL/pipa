from pipa.common.cmd import run_command
from psutil import cpu_count


def get_cpu_cores():
    """
    Returns a list of the number of CPU cores.

    This function uses the `lscpu` command to retrieve the number of CPU cores
    on the system. It parses the output of the command and returns a list of
    integers representing the number of CPU cores.

    Returns:
        list: A list of integers representing the number of CPU cores.

    Example:
        >>> get_cpu_cores()
        [0, 1, 2, 3, 4, 5, 6, 7]
    """
    cpu_list = [
        l
        for l in run_command("lscpu -p=cpu", log=False).split("\n")
        if not l.startswith("#")
    ]
    return [int(x) for x in cpu_list]


NUM_CORES_PHYSICAL = cpu_count(logical=False)  # Number of physical cores
