import pandas as pd
from pipa.common.logger import logger


def parse_one_line(s, lr):
    """
    Parse a single line of a performance report.

    Args:
        s (str): The input line to parse.
        lr (list): A list of tuples representing the start and end indices of each field in the line.

    Returns:
        tuple: A tuple containing the parsed values from the line in the following order:
            - overhead_cycles (float): The number of overhead cycles.
            - overhead_insns (float): The number of overhead instructions.
            - command (str): The command associated with the line.
            - shared_object (str): The shared object associated with the line.
            - execution_mode (str): The execution mode associated with the line.
            - symbol (str): The symbol associated with the line.
    """
    try:
        # TODO support more than two columns for the overhead percentage
        (
            overhead,
            command,
            shared_object,
            symbol,
        ) = (
            s[lr[0][0] : lr[0][1]],
            s[lr[1][0] : lr[1][1]],
            s[lr[2][0] : lr[2][1]],
            s[lr[3][0] :],
        )
        overhead_cycles, overhead_insns = overhead.split()
        execution_mode = symbol.split()[0]
        symbol = " ".join(symbol.split()[1:])
        execution_mode = execution_mode[1]
    except Exception as e:
        logger.warning("parse failed for line: " + s + "\n with error: " + str(e))
        return None
    return (
        float(overhead_cycles[:-1]),
        float(overhead_insns[:-1]),
        command.strip(),
        shared_object.strip(),
        execution_mode,
        symbol.strip(),
    )


def parse_perf_report_file(parsed_report_path):
    """
    Parses a performance report file and returns the parsed data as a pandas DataFrame.

    Args:
        parsed_report_path (str): The path to the parsed report file.

    Returns:
        pandas.DataFrame: The parsed data as a DataFrame with the following columns:
            - overhead_cycles: The number of overhead cycles.
            - overhead_insns: The number of overhead instructions.
            - command: The command associated with the performance data.
            - shared_object: The shared object associated with the performance data.
            - execution_mode: The execution mode associated with the performance data.
            - symbol: The symbol associated with the performance data.
    """
    lr = []
    with open(parsed_report_path, "r") as file:
        lines = file.readlines()
        for line in lines:
            if "......." in line:
                a = line.strip().removeprefix("#").split()
                for x in a:
                    if not lr:
                        l = line.index(x)
                        lr.append((l, l + len(x)))
                    else:
                        l = line.index(x, lr[-1][1])
                        lr.append((l, l + len(x)))
                break

    content = [l for l in lines if not l.startswith("#") and l.strip() != ""]

    if content is None:
        logger.info("content is None")
        return None

    data = [parse_one_line(l, lr) for l in content]

    data = [d for d in data if d is not None]

    logger.info("Successfully parsed data")
    logger.info("parsed data length: " + str(len(data)))

    return pd.DataFrame(
        data,
        columns=[
            "overhead_cycles",
            "overhead_insns",
            "command",
            "shared_object",
            "execution_mode",
            "symbol",
        ],
    )
