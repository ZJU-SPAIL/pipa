import questionary
from rich import print
from pipa.service.gengerate.common import (
    quest_basic,
    CORES_ALL,
    write_title,
    opener,
    parse_perf_data,
    move_old_file,
    generate_core_list,
)
from pipa.service.export_sys_config import write_export_config_script
import os


def quest():
    """
    This function prompts the user with a series of questions to gather information for running a workload.

    Returns:
        A tuple containing the following information:
        - workspace: The workspace path
        - freq_record: Frequency record
        - events_record: Events record
        - freq_stat: Frequency statistics
        - events_stat: Events statistics
        - annotete: Whether to use perf-annotate (True or False)
        - command: The command of the workload
    """
    config = quest_basic()

    use_taskset = questionary.select(
        "Whether to use taskset?\n", choices=["Yes", "No"]
    ).ask()

    if use_taskset == "Yes":
        cores_input: str = questionary.text(
            f"Which cores do you want to use? (Default: {CORES_ALL[0]}-{CORES_ALL[-1]})\n",
            f"{CORES_ALL[0]}-{CORES_ALL[-1]}",
        ).ask()

        core_list = generate_core_list(cores_input)

    command = questionary.text("What's the command of workload?\n").ask()

    if command == "":
        print("Please input a command to run workload.")
        exit(1)

    if use_taskset == "Yes":
        config["command"] = f"/usr/bin/taskset -c {core_list} {command}"
    else:
        config["command"] = command
    return config


def generate(config):
    """
    Generate a shell script for collecting performance data which start workload by perf.

    Args:
        config (dict): Configuration dictionary containing the following keys:
            - workspace (str): The path to the workspace directory.
            - freq_record (str): The frequency for recording events.
            - events_record (str): The events to be recorded.
            - freq_stat (str): The frequency for collecting statistics.
            - events_stat (str): The events to be collected for statistics.
            - annotete (bool): Whether to annotate the performance data.
            - command (str): The command to be executed.

    Returns:
        None
    """
    workspace = config["workspace"]
    freq_record = config["freq_record"]
    events_record = config["events_record"]
    count_delta_stat = config["count_delta_stat"]
    events_stat = config["events_stat"]
    annotete = config["annotete"]
    command = config["command"]
    use_emon = config["use_emon"]
    if use_emon:
        mpp = config["MPP_HOME"]
    with open(workspace + "/pipa-run.sh", "w", opener=opener) as f:
        write_title(f)

        f.write("WORKSPACE=" + workspace + "\n")
        move_old_file(f)

        f.write("mkdir -p $WORKSPACE\n\n")
        f.write("ps -aux -ef --forest --sort=-%cpu > $WORKSPACE/ps.txt\n")

        f.write(
            f"perf record -e '{events_record}' -g -a -F {freq_record} -o $WORKSPACE/perf.data {command}\n"
        )
        parse_perf_data(f)

        f.write("sar -o $WORKSPACE/sar.dat 1 >/dev/null 2>&1 &\n")
        f.write("sar_pid=$!\n")

        if use_emon:
            f.write(
                f"emon -i {mpp}/emon_event_all.txt -v -f $WORKSPACE/emon_result.txt -t 0.1 -l 100000000 -c -experimental -w {command} &\n"
            )
        else:
            f.write(
                f"perf stat -e {events_stat} -C {CORES_ALL[0]}-{CORES_ALL[-1]} -A -x , -I {count_delta_stat} -o $WORKSPACE/perf-stat.csv {command}\n"
            )

        f.write("kill -9 $sar_pid\n")
        f.write("LC_ALL='C' sar -A -f $WORKSPACE/sar.dat >$WORKSPACE/sar.txt\n\n")

        if use_emon:
            f.write(
                f"python {mpp}/mpp/mpp.py -i $WORKSPACE/emon_result.txt -m {mpp}/metrics/icelake_server_2s_nda.xml -o ./ --thread-view"
            )

        if annotete:
            f.write(
                "perf annotate -i $WORKSPACE/perf.data > $WORKSPACE/perf.annotate\n\n"
            )

        write_export_config_script(f, os.path.join(workspace, "config"))

        f.write("echo 'Performance data collected successfully.'\n")

        print("Shell script generated successfully.")
        print("Please check the script in " + workspace + "/pipa-run.sh")
        print(
            "Note that you may need to modify the script to meet your requirements.",
            "The core list is generated according to the machine which runs this script now.",
            "pipa-run.sh is more suitable for reproducible workloads such as benchmark.",
        )


def main():
    generate(quest())


if __name__ == "__main__":
    main()
