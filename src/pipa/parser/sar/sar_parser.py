import pandas as pd
import re
from pipa.common.cmd import run_command
from pipa.common.hardware.cpu import NUM_CORES_PHYSICAL
from pipa.common.logger import logger
from typing import List
import multiprocessing


# Parser class, responsible for parsing SAR data
class SarParser:
    @staticmethod
    def parse_sar_bin_to_txt(sar_bin_path: str) -> List[str]:
        """
        Parses the SAR binary file into a list of lines.

        Args:
            sar_bin_path (str): Path to the SAR binary file.

        Returns:
            list: List of lines in the SAR binary file.
        """
        sar_lines = run_command(f"LC_ALL='C' sar -A -f {sar_bin_path}").split("\n")
        return sar_lines

    @staticmethod
    def split_sar_block(sar_lines: List[str]) -> List[List[str]]:
        """
        Splits the SAR block into individual blocks by '\n'.

        Args:
            sar_lines (list): List of SAR output lines.

        Returns:
            list: List of individual SAR blocks.
        """
        sar_lines = [l.strip() for l in sar_lines]
        return [
            list(filter(None, p.split("\n")))
            for p in "\n".join(sar_lines).split("\n\n")
        ]

    @staticmethod
    def trans_time_to_seconds(df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms the timestamp column in the given DataFrame to seconds.

        Note this function sees each non-descending queue as a seperate day and raw timestamp format is %H:%M:%S.

        Thus this function can't deal with those interval more than 1 day, like: ["00:00:00", "00:00:00"].
        We see as the same time and parse it as ["1900-01-01 00:00:00", "1900-01-01 00:00:00"], but it also can be ["1900-01-01 00:00:00", "1900-01-02 00:00:00"].

        We are now try to use sadf instead of rewriting parsing sar file directly.

        Args:
            df (pandas.DataFrame): The DataFrame containing the timestamp column.

        Returns:
            pandas.DataFrame: The DataFrame with the timestamp column transformed to seconds.
        """
        day_prefix = 0
        result = []
        base_date = pd.Timestamp("1900-01-01")
        # iter all timestamp and add day prefix
        for i, ts in enumerate(df["timestamp"]):
            # switch to next day
            if i > 0 and ts < df["timestamp"].iloc[i - 1]:
                day_prefix += 1
            result.append(
                base_date + pd.Timedelta(days=day_prefix) + pd.to_timedelta(ts)
            )
        df["timestamp"] = result

        try:
            df["timestamp"] -= df.loc[:, "timestamp"].iloc[0]
            df["timestamp"] = df["timestamp"].dt.total_seconds()
        except IndexError as e:
            logger.warning(
                f"{df.columns.to_list()} column may has wrong format, please check the origin sar data"
            )
        return df

    @staticmethod
    def merge_one_line(sar_line: str) -> List[str]:
        """
        Merge a single line of SAR data into a list.

        Args:
            sar_line (str): The SAR data line to be merged.

        Returns:
            list: The merged SAR data as a list.
        """
        sar_line = sar_line.split()
        if sar_line[1] in ["AM", "PM"]:
            sar_line.pop(1)
        return sar_line

    @staticmethod
    def add_post_fix(sar_line: List[str], len_columns: int) -> List[str]:
        """
        Adds post-fix to the given SAR line to match the specified number of columns.

        Args:
            sar_line (list): The SAR line to add post-fix to.
            len_columns (int): The desired number of columns.

        Returns:
            list: The SAR line with post-fix added to match the specified number of columns.
        """
        while len(sar_line) < len_columns:
            sar_line.append("")
        if len(sar_line) > len_columns:
            sar_line[len_columns - 1] += " ".join(sar_line[len_columns:])
        return sar_line[:len_columns]

    @staticmethod
    def process_subtable(
        sar_columns: List[str],
        sar_blocks: List[str],
        processes_num=min(12, NUM_CORES_PHYSICAL),
    ) -> List[List[str]]:
        """
        Process the subtable data by merging lines and adding post-fixes.

        Args:
            sar_columns (list): List of SAR columns.
            sar_blocks (list): List of SAR blocks.
            processes_num (int, optional): Number of processes to use for parallel processing.
                Defaults to the minimum of 12 and the number of physical CPU cores.

        Returns:
            list: List of processed subtable data.

        """
        if len(sar_blocks) <= 10**6 or processes_num <= 1:
            # if the number of lines is less than 1e6, use single process
            return [
                SarParser.add_post_fix(SarParser.merge_one_line(x), len(sar_columns))
                for x in sar_blocks
            ]
        pool = multiprocessing.Pool(processes=processes_num)
        merged_lines = pool.map(SarParser.merge_one_line, sar_blocks)
        res = pool.starmap(
            SarParser.add_post_fix,
            zip(merged_lines, [len(sar_columns) for _ in range(len(merged_lines))]),
        )
        pool.close()
        pool.join()
        return res

    @staticmethod
    def sar_to_df(sar_blocks: List[str]) -> pd.DataFrame:
        """
        Convert SAR blocks to a pandas DataFrame.

        Args:
            sar_blocks (list): A list of SAR blocks.

        Returns:
            pandas.DataFrame: A DataFrame containing the processed SAR data.

        """
        while sar_blocks[0] == "":
            sar_blocks = sar_blocks[1:]

        time_pattern = r"\d{2}:\d{2}:\d{2}"
        sar_columns = sar_blocks[0].split()
        if re.match(time_pattern, sar_columns[0]):
            sar_columns = ["timestamp"] + sar_columns[1:]
        return pd.DataFrame(
            SarParser.process_subtable(sar_columns, sar_blocks[1:]),
            columns=sar_columns,
        )

    @staticmethod
    def parse_sar_bin(sar_bin_path: str) -> List[pd.DataFrame]:
        """
        Parses the SAR binary file and returns a list of dataframes.

        Args:
            sar_bin_path (str): The path to the SAR binary file.

        Returns:
            List[pd.DataFrame]: A list of dataframes containing the parsed SAR data.
        """
        sar_content = SarParser.parse_sar_bin_to_txt(sar_bin_path)
        return SarParser.parse_sar_string(sar_content)

    @staticmethod
    def parse_sar_txt(sar_txt_path: str) -> List[pd.DataFrame]:
        """
        Parses the SAR text file and returns a list of dataframes.

        Args:
            sar_txt_path (str): The path to the SAR text file.

        Returns:
            List[pd.DataFrame]: A list of dataframes containing the parsed SAR data.
        """
        with open(sar_txt_path, "r") as f:
            sar_content = f.readlines()
        return SarParser.parse_sar_string(sar_content)

    @staticmethod
    def parse_sar_string(sar_string: List[str]) -> List[pd.DataFrame]:
        """
        Parses the SAR string and returns a list of dataframes.

        Args:
            sar_string (str): The string containing the SAR data.

        Returns:
            List[pd.DataFrame]: A list of dataframes containing the parsed SAR data.
        """
        sar_data = SarParser.split_sar_block(sar_string)[1:]
        a = [SarParser.sar_to_df(d) for d in sar_data]
        l = 0
        res = []
        while l < len(a):  # merge dataframes with the same columns, use two pointers
            r = l + 1
            while r < len(a) and a[r].columns.equals(a[l].columns):
                r += 1
            res.append(pd.concat(a[l:r], axis=0))
            l = r
        return res
