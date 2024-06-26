import questionary
from rich import print
from pipa.service.gengerate.common import quest_basic, CORES_ALL, write_title


def quest():
    workspace, freq_record, events_record, freq_stat, events_stat, annotete = (
        quest_basic()
    )

    set_record = questionary.select(
        "Whether to set the duration of the perf-record run?\n",
        choices=["Yes", "No, I'll control it by myself. (Exit by Ctrl+C)"],
    ).ask()

    record_time, stat_time = None, None

    if set_record == "Yes":
        record_time = questionary.text(
            "How long do you want to run perf-record? (Default: 120s)\n", "120"
        ).ask()

    set_stat = questionary.select(
        "Whether to set the duration of the perf-stat run?\n",
        choices=["Yes", "No, I'll control it by myself. (Exit by Ctrl+C)"],
    ).ask()
    if set_stat == "Yes":
        stat_time = questionary.text(
            "How long do you want to run perf-stat? (Default: 120s)\n", "120"
        ).ask()

    return (
        workspace,
        freq_record,
        events_record,
        freq_stat,
        events_stat,
        annotete,
        record_time,
        stat_time,
    )


def generate(
    workspace,
    freq_record,
    events_record,
    freq_stat,
    events_stat,
    annotete,
    record_time,
    stat_time,
):
    with open(workspace + "/pipa-collect.sh", "w") as f:
        write_title(f)

        f.write("WORKSPACE=" + workspace + "\n")
        f.write("mkdir -p $WORKSPACE\n\n")

        f.write("ps -aux -ef --forest > $WORKSPACE/ps.txt\n")

        f.write(
            f"perf record -e '{events_record}' -a -F"
            + f" {freq_record} -o $WORKSPACE/perf.data"
            + f" -- sleep {record_time}\n"
            if record_time
            else "\n"
        )

        f.write("sar -o $WORKSPACE/sar.dat 1 >/dev/null 2>&1 &\n")
        f.write("sar_pid=$!\n")
        f.write(
            f"perf stat -e {events_stat} -C {CORES_ALL[0]}-{CORES_ALL[-1]} -A -x , -I {freq_stat} -o $WORKSPACE/perf-stat.csv"
            + f" sleep {stat_time}\n"
            if stat_time
            else "\n"
        )
        f.write("kill -9 $sar_pid\n")

        f.write("echo 'Performance data collected successfully.'\n")

    with open(workspace + "/pipa-parse.sh", "w") as f:
        write_title(f)
        f.write("WORKSPACE=" + workspace + "\n")
        f.write("perf script -i $WORKSPACE/perf.data > $WORKSPACE/perf.script\n")
        f.write("perf report -i $WORKSPACE/perf.data > $WORKSPACE/perf.report\n\n")
        f.write("sar -A -f $WORKSPACE/sar.dat >$WORKSPACE/sar.txt\n\n")

        if annotete:
            f.write(
                "perf annotate -i $WORKSPACE/perf.data > $WORKSPACE/perf.annotate\n\n"
            )

        f.write("echo 'Performance data parsed successfully.'\n")

        print("Shell script generated successfully.")
        print("Please check the script in " + workspace + "/pipa-collect.sh")


def main():
    generate(*quest())


if __name__ == "__main__":
    main()
