import pandas as pd
import re
from pipa.common.logger import logger
import multiprocessing
from pipa.export_config.cpu_config import NB_PHYSICAL_CORES


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
        except:
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


def parse_perf_script_file(parsed_script_path, processes_num=NB_PHYSICAL_CORES):
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
            "caller",
        ],
    )


if __name__ == "__main__":
    parse_perf_script_file(input("input perf script text data path:"))
