import questionary
from pipa.common.hardware.cpu import get_cpu_cores
from rich import print
from io import TextIOWrapper
from datetime import datetime


import os
import yaml


def ask_number(question: str, default: int) -> int:
    """
    Asks the user to input a number based on the given question and default value.

    Args:
        question (str): The question to ask the user.
        default (int): The default value to return if the user doesn't input anything.

    Returns:
        int: The number inputted by the user or the default value.
    """
    result = questionary.text(question, str(default)).ask().strip()

    if result == "":
        return default
    elif result.isdigit():
        return int(result)
    else:
        print("Please input a number.")
        exit(1)


CORES_ALL = get_cpu_cores()


def quest_basic():
    """
    Asks the user a series of questions to gather basic information for data storage and performance recording.

    Returns:
        dict: A dictionary containing the user's choices for workspace, frequency of perf-record, event of perf-record,
              whether to use perf-annotate, whether to use perf-stat or emon, count deltas of perf-stat, events of perf-stat,
              and the location of mpp if emon is chosen.

    Raises:
        ValueError: If an invalid choice is made.
    """
    workspace = questionary.text(
        "Where do you want to store your data? (Default: ./)\n", "./"
    ).ask()

    if workspace == "":
        workspace = "./"

    if not os.path.exists(workspace):
        os.makedirs(workspace)

    freq_record = ask_number(
        "What's the frequency of perf-record? (Default: 999)\n", 999
    )
    events_record = questionary.text(
        "What's the event of perf-record? (Default: {cycles,instructions}:S)\n",
        "{cycles,instructions}:S",
    ).ask()

    annotete = questionary.select(
        "Whether to use perf-annotate?\n", choices=["Yes", "No"], default="No"
    ).ask()
    annotete = True if annotete == "Yes" else False

    stat = questionary.select(
        "Do you want to use perf-stat or emon?\n",
        choices=["perf-stat", "emon"],
        default="perf-stat",
    ).ask()

    if stat == "perf-stat":
        freq_stat = ask_number(
            "What's count deltas of perf-stat? (Default: 1000 milliseconds)\n", 1000
        )
        events_stat = questionary.text(
            "What's the event of perf-stat?\n",
            "cycles,instructions,branch-misses,L1-dcache-load-misses,L1-icache-load-misses",
        ).ask()
        return {
            "workspace": workspace,
            "freq_record": freq_record,
            "events_record": events_record,
            "use_emon": False,
            "count_delta_stat": freq_stat,
            "events_stat": events_stat,
            "annotete": annotete,
        }
    elif stat == "emon":
        mpp = questionary.text(
            "Where is the mpp?\n",
            "/mnt/hdd/share/emon/system_health_monitor",
        ).ask()
        return {
            "workspace": workspace,
            "freq_record": freq_record,
            "events_record": events_record,
            "use_emon": True,
            "mpp": mpp,
            "annotete": annotete,
        }

    raise ValueError("Invalid choice.")


def generate_core_list(core_range: str, only_comma: bool = False) -> str:
    """Generate right core list by core_range

    The core range should be like:
    1. a single digit like '8' means the 8 core
    2. a range like '1-8' means the cores from 1 to 8
    3. a range like '1-8,9-12' means the cores from 1 to 8 and from 9 to 12

    Args:
        core_range (str): the input core range
        only_comma (bool): return only comma split core range

    Raises:
        ValueError: If get a illegal core range

    Returns:
        str: the right core range
    """
    core_range = core_range.split(",")
    core_range_list: list[str] = []
    for r in core_range:
        if r.isdigit():
            d = int(r)
            if d < CORES_ALL[0] or d > CORES_ALL[-1]:
                raise ValueError(f"Please input core in a valid range: {d}")
            core_range_list.append(r.strip())
        elif r.split("-").__len__() != 2:
            raise ValueError(f"Please input cores as a valid range, split by '-': {r}")
        else:
            left, right = r.split("-")

            left, right = left.strip(), right.strip()
            if not left.isdigit() or not right.isdigit():
                raise ValueError(
                    f"Please input cores as a valid range, non-digit char detected: {r}"
                )
            left, right = int(left), int(right)
            if left < CORES_ALL[0] or right > CORES_ALL[-1] or left > right:
                raise ValueError(f"Please input cores as a valid range: {r}")
            if only_comma:
                core_range_list.append(
                    ",".join([str(x) for x in range(left, right + 1)])
                )
            else:
                core_range_list.append(f"{left}-{right}")
    return ",".join(core_range_list)


def write_title(file: TextIOWrapper):
    """
    Writes the title section to the given file.

    Args:
        file (TextIOWrapper): The file object to write the title section to.
    """
    current_time = datetime.now().isoformat()
    file.write(
        f"""#!/bin/bash
# The script generated by PIPA-TREE is used to collect performance data.
# Please check whether it meets expectations before running.
# ZJU SPAIL(https://github.com/ZJU-SPAIL) reserves all rights.
# Generated at {current_time}

# Check if sar and perf are available
if ! command -v sar &> /dev/null; then
echo "sar command not found. Please install sar."
exit 1
fi

if ! command -v perf &> /dev/null; then
echo "perf command not found. Please install perf."
exit 1
fi\n\n"""
    )


def move_old_file(file: TextIOWrapper):
    return file.write(
        """# Check if $workspace exists
if [ -d "$workspace" ]; then
  # Check if perf-stat.csv or sar.dat exists in $workspace
  if [ -f "$workspace/perf-stat.csv" ] || [ -f "$workspace/sar.dat" ]; then
    # Move $workspace to $workspace_old
    mv "$workspace" "${workspace}_old"
  fi
fi\n"""
    )


def parse_perf_data(file: TextIOWrapper):
    """
    Parses the performance data and writes it to the given file.

    Args:
        file (TextIOWrapper): The file object to write the performance data to.
    """
    return file.write(
        """perf script -i $WORKSPACE/perf.data -I --header > $WORKSPACE/perf.script\n
perf report -i $WORKSPACE/perf.data -I --header > $WORKSPACE/perf.report\n
perf buildid-list -i $WORKSPACE/perf.data > $WORKSPACE/perf.buildid\n\n"""
    )


def load_yaml_config(file_path: str = "config-pipa-shu.yaml") -> dict:
    """
    Parses a YAML file and returns the contents as a dictionary.

    Args:
        file_path (str): The path to the YAML file.

    Returns:
        dict: The contents of the YAML file as a dictionary.
    """
    with open(file_path, "r") as file:
        data = yaml.safe_load(file)
    return data


def opener(path, flags):
    """
    Opens a file at the given path with the specified flags.
    Mode is set to 0o755.

    Args:
        path (str): The path to the file.
        flags (int): The flags to use when opening the file.

    Returns:
        int: The file descriptor of the opened file.
    """
    descriptor = os.open(path=path, flags=flags, mode=0o755)
    return descriptor
