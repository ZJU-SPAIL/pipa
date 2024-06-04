import pandas as pd
import re
from pipa.common.cmd import run_command


def parse_sar_bin_to_txt(sar_bin_path: str):
    """
    Parses the SAR binary file into a list of lines.

    Args:
        sar_bin_path (str): Path to the SAR binary file.

    Returns:
        list: List of lines in the SAR binary file.
    """
    sar_lines = run_command(f"sar -A -f {sar_bin_path}").split("\n")
    return sar_lines


def split_sar_block(sar_lines: list):
    """
    Splits the SAR block into individual blocks by '\n'.

    Args:
        sar_lines (list): List of SAR output lines.

    Returns:
        list: List of individual SAR blocks.
    """
    sar_lines = [l.strip() for l in sar_lines]
    return [
        list(filter(None, p.split("\n"))) for p in "\n".join(sar_lines).split("\n\n")
    ]


def trans_time_to_24h(time: str) -> str:
    time = time.split()
    if time[-1] == "PM":
        h, m, s = time[0].split(":")
        h = str(int(time[0].split(":")[0]) + 12)
        time[0] = ":".join([h, m, s])
    return time[0]


def merge_one_line(sar_line: str) -> list:
    sar_line = sar_line.split()
    sar_line[0] = trans_time_to_24h(sar_line[0] + " " + sar_line[1])
    sar_line.pop(1)
    return sar_line


def add_post_fix(sar_line: list, len_columns: int):
    while len(sar_line) < len_columns:
        sar_line.append("")
    if len(sar_line) > len_columns:
        sar_line[len_columns - 1] += " ".join(sar_line[len_columns:])
    return sar_line[:len_columns]


def sar_to_df(sar_blocks: list):
    if sar_blocks[0] == "":
        sar_blocks.pop(0)

    time_pattern = r"\d{2}:\d{2}:\d{2}"
    if re.match(time_pattern, sar_blocks[0].split()[0]):
        sar_columns = ["timestamp"] + sar_blocks[0].split()[2:]
        sar_data = [
            add_post_fix(merge_one_line(x), len(sar_columns)) for x in sar_blocks[1:]
        ]
    else:
        sar_columns = sar_blocks[0].split()
        sar_data = [add_post_fix(x.split(), len(sar_columns)) for x in sar_blocks[1:]]
    return pd.DataFrame(
        sar_data,
        columns=sar_columns,
    )


def parse_sar_bin(sar_bin_path: str):
    """
    Parses the SAR binary file and returns a list of dataframes.

    Args:
        sar_bin_path (str): The path to the SAR binary file.

    Returns:
        List[pd.DataFrame]: A list of dataframes containing the parsed SAR data.
    """
    sar_content = parse_sar_bin_to_txt(sar_bin_path)
    return parse_sar_string(sar_content)


def parse_sar_txt(sar_txt_path: str):
    """
    Parses the SAR text file and returns a list of dataframes.

    Args:
        sar_txt_path (str): The path to the SAR text file.

    Returns:
        List[pd.DataFrame]: A list of dataframes containing the parsed SAR data.
    """
    with open(sar_txt_path, "r") as f:
        sar_content = f.readlines()
    return parse_sar_string(sar_content)


def parse_sar_string(sar_string: str):
    """
    Parses the SAR string and returns a list of dataframes.

    Args:
        sar_string (str): The string containing the SAR data.

    Returns:
        List[pd.DataFrame]: A list of dataframes containing the parsed SAR data.
    """
    sar_data = split_sar_block(sar_string)[1:]
    return [sar_to_df(d) for d in sar_data]


def filter_CPU_Utilization(sar_txt_path: str):
    with open(sar_txt_path, "r") as f:
        sar_content = f.readlines()
    sar_data = [
        i
        for i in split_sar_block(sar_content)[1:]
        if i[0].endswith(
            "CPU      %usr     %nice      %sys   %iowait    %steal      %irq     %soft    %guest    %gnice     %idle"
        )
    ]
    return [sar_to_df(d) for d in sar_data]
