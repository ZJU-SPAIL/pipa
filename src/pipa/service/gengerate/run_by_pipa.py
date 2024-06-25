import questionary
from rich import print
from pipa.service.gengerate.common import quest_basic, CORES_ALL, write_title


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
    workspace, freq_record, events_record, freq_stat, events_stat, annotete = (
        quest_basic()
    )

    use_taskset = questionary.select(
        "Whether to use taskset?\n", choices=["Yes", "No"]
    ).ask()

    if use_taskset == "Yes":
        cores_input = questionary.text(
            "Which cores do you want to use? (Default: 120-140)\n", "120-140"
        ).ask()

        if cores_input.isdigit():
            core_list = cores_input.strip()
        elif cores_input.split("-").__len__() != 2:
            print("Please input a valid range, split by '-'.")
            exit(1)
        else:
            left, right = cores_input.split("-")

            left, right = left.strip(), right.strip()
            if not left.isdigit() or not right.isdigit():
                print("Please input a valid range, non-digit char detected.")
                exit(1)
            left, right = int(left), int(right)
            if left < CORES_ALL[0] or right > CORES_ALL[-1] or left > right:
                print("Please input a valid range.")
                exit(1)
            core_list = ",".join([str(i) for i in list(range(left, right + 1))])

    command = questionary.text("What's the command of workload?\n").ask()

    if command == "":
        print("Please input a command to run workload.")
        exit(1)

    if use_taskset == "Yes":
        command = f"/usr/bin/taskset -c {core_list} {command}"
    return (
        workspace,
        freq_record,
        events_record,
        freq_stat,
        events_stat,
        annotete,
        command,
    )


def generate(
    workspace, freq_record, events_record, freq_stat, events_stat, annotete, command
):
    """
    Generate a shell script for collecting performance data which start workload by perf.

    Args:
        workspace (str): The path to the workspace directory.
        freq_record (str): The frequency for recording events.
        events_record (str): The events to be recorded.
        freq_stat (str): The frequency for collecting statistics.
        events_stat (str): The events to be collected for statistics.
        annotete (bool): Whether to annotate the performance data.
        command (str): The command to be executed.

    Returns:
        None
    """
    with open(workspace + "/pipa-run.sh", "w") as f:
        write_title(f)

        f.write("WORKSPACE=" + workspace + "\n")
        f.write("mkdir -p $WORKSPACE\n\n")

        f.write("ps -aux -ef --forest > $WORKSPACE/ps.txt\n")

        f.write(
            f"perf record -e '{events_record}' -a -F"
            + f" {freq_record} -o $WORKSPACE/perf.data {command}\n"
        )
        f.write("perf script -i $WORKSPACE/perf.data > $WORKSPACE/perf.script\n")
        f.write("perf report -i $WORKSPACE/perf.data > $WORKSPACE/perf.report\n\n")

        f.write("sar -o $WORKSPACE/sar.dat 1 >/dev/null 2>&1 &\n")
        f.write("sar_pid=$!\n")
        f.write(
            f"perf stat -e {events_stat} -C {CORES_ALL[0]}-{CORES_ALL[-1]} -A -x , -I {freq_stat} -o $WORKSPACE/perf-stat.csv {command}\n"
        )
        f.write("kill -9 $sar_pid\n")
        f.write("sar -A -f $WORKSPACE/sar.dat >$WORKSPACE/sar.txt\n\n")

        if annotete:
            f.write(
                "perf annotate -i $WORKSPACE/perf.data > $WORKSPACE/perf.annotate\n\n"
            )

        f.write("echo 'Performance data collected successfully.'\n")

        print("Shell script generated successfully.")
        print("Please check the script in " + workspace + "/pipa-run.sh")


def main():
    generate(*quest())


if __name__ == "__main__":
    main()
