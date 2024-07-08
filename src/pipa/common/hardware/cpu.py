from pipa.common.cmd import run_command


def get_cpu_cores():
    cpu_list = [
        l
        for l in run_command("lscpu -p=cpu", log=False).split("\n")
        if not l.startswith("#")
    ]
    return [int(x) for x in cpu_list]
