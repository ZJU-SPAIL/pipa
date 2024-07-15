import pandas as pd
import re
import multiprocessing
import os
from pipa.common.logger import logger
from pipa.common.hardware.cpu import NUM_CORES_PHYSICAL
from pandarallel import pandarallel


class PerfScriptData:
    def __init__(self, parsed_script_path: str):
        if not os.path.exists(parsed_script_path):
            logger.error(f"File not found: {parsed_script_path}")
            raise FileNotFoundError()
        self._perf_script_data = parse_perf_script_file(parsed_script_path)

        if len(self._perf_script_data) == 0:
            logger.warning("No data found in the perf script file.")

        if len(self._perf_script_data) >= 10**6:
            threads_num = min(12, NUM_CORES_PHYSICAL)
            logger.info(f"Using pandarallel to speed up, threads_num is {threads_num}.")
            pandarallel.initialize(nb_workers=threads_num)

        self._df_wider = None

    def get_raw_data(self):
        return self._perf_script_data

    def get_wider_data(self):
        """
        Tidy data by merging cycles and instructions data.

        Returns:
            pandas.DataFrame: The tidied data as a DataFrame.
        """
        if self._df_wider is not None:
            return self._df_wider

        df = self._perf_script_data
        df_cycles = df.query("event == 'cycles'")
        df_insns = df.query("event == 'instructions'")
        df_wider = (
            df_cycles.merge(
                df_insns,
                on=[
                    "time",
                    "cpu",
                    "command",
                    "pid",
                    "addr",
                    "symbol",
                    "dso_short_name",
                ],
                suffixes=("_cycles", "_insns"),
            )
            .drop(columns=["event_cycles", "event_insns"])
            .rename(
                {
                    "value_cycles": "cycles",
                    "value_insns": "instructions",
                },
                axis=1,
            )
        )

        self._df_wider = df_wider[
            [
                "command",
                "pid",
                "cpu",
                "time",
                "cycles",
                "instructions",
                "addr",
                "symbol",
                "dso_short_name",
            ]
        ]
        self._df_wider["CPI"] = df_wider["cycles"] / df_wider["instructions"]
        return self._df_wider


def parse_one_line(line):
    """
    Parses a single line of input and returns a list of parsed values.

    Args:
        line (str): The input line to be parsed.

    Returns:
        list: A list containing the parsed values from the input line.
            The list contains the following elements in order:
            - command (str): The command name.
            - pid (int): The process ID.
            - tid (int): The thread ID.
            - cpu (int): The CPU number.
            - time (str): The time value.
            - value (int): The event value.
            - event (str): The event name.
            - addr (str): The address value.
            - symbol (str): The symbol name.
            - caller (str): The caller value.
    """
    try:
        try:
            pattern = r"(\S+|\:-\d+)\s+(\d+|-\d+)\s+\[(\d+)]\s+(\d+\.\d+):\s+(\d+)\s+(\S+):\s+(\S+)\s+(.*?)\s+\((\S+)\)"

            command, pid, cpu, time, value, event, addr, symbol, caller = re.match(
                pattern, line.strip()
            ).groups()
        except Exception as e:
            pattern = r"(\d+|-\d+)\s+\[(\d+)]\s+(\d+\.\d+):\s+(\d+)\s+(\S+):\s+(\S+)\s+(.*?)\s+\((\S+)\)"
            (
                pid,
                cpu,
                time,
                value,
                event,
                addr,
                symbol,
                caller,
            ) = re.match(pattern, line[15:].strip()).groups()

            command = line[:15].strip()

    except Exception as e:
        logger.warning("parse failed for line: " + line + "\n with error: " + str(e))
        return None

    return [
        command,
        int(pid),
        int(cpu),
        time,
        int(value),
        event,
        addr,
        symbol,
        caller,
    ]


def parse_perf_script_file(parsed_script_path: str, processes_num=NUM_CORES_PHYSICAL):
    """
    Parses a perf script file and returns the data as a pandas DataFrame.

    Args:
        parsed_script_path (str): The path to the perf script file.

    Returns:
        pandas.DataFrame: The parsed data as a DataFrame.
    """

    # Open the perf script file in read mode
    with open(parsed_script_path, "r") as file:
        # Read all lines from the file and remove leading/trailing whitespaces
        content = [l.strip() for l in file.readlines()]

    # Ensure that the content is not None
    if content is None:
        logger.info("content is None")
        return None

    # Define the separator used to split the header and table sections
    SEPARATOR = "# ========"

    # Check if the first line is the separator, and remove it if present
    if content[0] == SEPARATOR:
        content.pop(0)

    if SEPARATOR in content:
        # Find the index of the separator in the content list
        sep_idx = content.index(SEPARATOR)

        # Split the content into header and table sections
        header, table = content[:sep_idx], content[sep_idx + 2 :]
    else:
        table = content

    pool = multiprocessing.Pool(processes=processes_num)
    data = pool.map(parse_one_line, table)
    pool.close()
    pool.join()

    data = [d for d in data if d is not None]

    # Parse each line in the table section and create a DataFrame
    return pd.DataFrame(
        data,
        columns=[
            "command",
            "pid",
            "cpu",
            "time",
            "value",
            "event",
            "addr",
            "symbol",
            "dso_short_name",
        ],
    )


if __name__ == "__main__":
    parse_perf_script_file(input("input perf script text data path:"))
