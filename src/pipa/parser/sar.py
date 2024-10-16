import pandas as pd
import seaborn as sns
import re
from pipa.common.cmd import run_command
from pipa.common.hardware.cpu import NUM_CORES_PHYSICAL
import multiprocessing


class SarData:
    def __init__(self, sar_string: str):
        """
        Initialize a SAR object with the given SAR string.

        Args:
            sar_string (str): The SAR string to parse.

        """
        self.sar_data: list[pd.DataFrame] = parse_sar_string(sar_string)

    @classmethod
    def init_with_sar_txt(cls, sar_txt_path: str):
        """
        Initializes the SarData object using a SAR text file.

        Args:
            sar_txt_path (str): Path to the SAR text file.

        Returns:
            SarData: Initialized SarData object.
        """
        with open(sar_txt_path, "r") as f:
            sar_content = f.readlines()
        return cls(sar_content)

    @classmethod
    def init_with_sar_bin(cls, sar_bin_path: str):
        """
        Initializes the SarData object using a SAR binary file.

        Args:
            sar_bin_path (str): Path to the SAR binary file.

        Returns:
            SarData: Initialized SarData object.
        """
        sar_content = parse_sar_bin_to_txt(sar_bin_path)
        return cls(sar_content)

    def filter_dataframe(self, df, data_type: str = "detail"):
        """
        Filters the given dataframe based on the specified data type.

        Parameters:
        - df: pandas.DataFrame
            The dataframe to be filtered.
        - data_type: str, optional
            The type of data to filter. Valid values are "detail", "raw", and "average".
            Defaults to "detail".

        Returns:
        - pandas.DataFrame
            The filtered dataframe.

        Raises:
        - ValueError: If an invalid data type is provided.
        """
        match data_type:
            case "detail":
                return df[df["timestamp"] != "Average:"]
            case "raw":
                return df
            case "average":
                return df[df["timestamp"] == "Average:"]
            case _:
                raise ValueError("Invalid type")

    def get_CPU_utilization(self, data_type: str = "detail"):
        """
        Retrieves the CPU utilization data from the SAR data.

        Args:
            data_type (str, optional): The type of CPU utilization data to retrieve. Defaults to "detail".
            Valid values are "detail", "raw", and "average".

        Returns:
            DataFrame: The filtered DataFrame containing the CPU utilization data.
        """
        util = self.filter_dataframe(self.sar_data[0], data_type).astype(
            {
                r"%usr": "float64",
                r"%nice": "float64",
                r"%sys": "float64",
                r"%iowait": "float64",
                r"%irq": "float64",
                r"%soft": "float64",
                r"%steal": "float64",
                r"%guest": "float64",
                r"%gnice": "float64",
                r"%idle": "float64",
            }
        )
        util[r"%util"] = 100 - util[r"%idle"]
        return util

    def get_CPU_util_avg_by_threads(self, threads: list = None):
        """
        Retrieves the average CPU utilization detailed data for the specified threads.

        Args:
            threads (list): List of CPU threads to retrieve the utilization data for.
                            If None, retrieves the utilization data for all threads. Defaults to None.

        Returns:
            DataFrame: The filtered DataFrame containing the CPU utilization data for the specified threads.
        """
        util = self.get_CPU_utilization("average")
        util_threads = (
            util[util["CPU"].isin([str(t) for t in threads])]
            if threads
            else util[util["CPU"] == "all"]
        )
        return util_threads

    def get_CPU_util_avg_summary(self, threads: list = None):
        """
        Retrieves the average CPU utilization summary for the specified threads.

        Args:
            threads (list, optional): List of CPU threads to retrieve the utilization summary for. If None, retrieves
                                      the summary for all threads. Defaults to None.

        Returns:
            dict: A dictionary containing the average CPU utilization summary.
        """
        util_threads = self.get_CPU_util_avg_by_threads(threads)
        return util_threads.drop(columns=["timestamp", "CPU"]).mean().to_dict()

    def plot_CPU_util_time(self, threads: list = None):
        """
        Plots the CPU utilization over time.

        Args:
            threads (list, optional): List of CPU threads to plot. If None, plots the utilization for all threads.
                                      Defaults to None.
        """
        df = self.get_CPU_utilization()
        df = (
            df[df["CPU"].isin([str(t) for t in threads])]
            if threads
            else df.query("CPU=='all'")
        )
        df = trans_time_to_seconds(df)

        if threads and len(threads) > 1:
            sns.lineplot(data=df, x="timestamp", y=r"%util", hue="CPU")
        else:
            sns.lineplot(data=df, x="timestamp", y=r"%util")

    def get_CPU_frequency(self, data_type: str = "detail"):
        """
        Returns the CPU frequency data.

        Args:
            data_type (str, optional): The type of CPU freqency data to retrieve. Defaults to "detail".

        Returns:
            pd.DataFrame: Dataframe containing the CPU frequency data.
        """
        return self.filter_dataframe(self.sar_data[31], data_type).astype(
            {"MHz": "float64"}
        )

    def plot_CPU_freq_time(self, threads: list = None):
        """
        Plots the CPU frequency over time.

        Args:
            threads (list, optional): List of CPU threads to plot. If None, plots the frequency for all threads.
                                      Defaults to None.
        """
        df = self.get_CPU_frequency()

        sns.set_theme(style="darkgrid", rc={"figure.figsize": (15, 8)})

        df = (
            df[df["CPU"].isin([str(t) for t in threads])]
            if threads
            else df.query("CPU=='all'")
        )
        df = trans_time_to_seconds(df)

        if threads and len(threads) > 1:
            sns.lineplot(
                data=df,
                x="timestamp",
                y="MHz",
                hue="CPU",
            )
        else:
            sns.lineplot(data=df, x="timestamp", y="MHz")

    def get_cpu_freq_avg(self, threads: list = None):
        """
        Returns the average CPU frequency data for the specified threads.

        Args:
            threads (list, optional): List of CPU threads to retrieve the frequency data for. If None, retrieves the
                                      frequency data for all threads. Defaults to None.

        Returns:
            dict: A dictionary containing the average CPU frequency data for the specified threads.
        """
        df = self.get_CPU_frequency("average")
        df = df[df["CPU"].isin([str(t) for t in threads])] if threads else df
        if df.empty:
            return {"cpu_frequency_mhz": 0}
        return {"cpu_frequency_mhz": df["MHz"].mean()}

    def get_CPU_util_freq(self, data_type: str = "detail"):
        """
        Returns the CPU utilization and frequency data.

        Args:
            data_type (str, optional): The type of CPU utilization and frequency data to retrieve. Defaults to "detail".

        Returns:
            pd.DataFrame: Dataframe containing the CPU utilization and frequency data.
        """
        util, freq = self.get_CPU_utilization(data_type), self.get_CPU_frequency(
            data_type
        )
        return pd.merge(util, freq, on=["timestamp", "CPU"])

    def get_network_statistics(
        self, data_type: str = "detail", on_failures: bool = False
    ):
        """Get

        Args:
            data_type (str, optional): _description_. Defaults to "detail".
            on_failures (bool, optional): _description_. Defaults to False.

        Returns:
            _type_: _description_
        """
        sar_loc = 13 if on_failures else 12
        astype_t = (
            {
                "IFACE": str,
                "rxerr/s": float,
                "txerr/s": float,
                "coll/s": float,
                "rxdrop/s": float,
                "rxdrop/s": float,
                "txcarr/s": float,
                "rxfram/s": float,
                "rxfifo/s": float,
                "txfifo/s": float,
            }
            if on_failures
            else {
                "IFACE": str,
                "rxpck/s": float,
                "txpck/s": float,
                "rxkB/s": float,
                "txkB/s": float,
                "rxcmp/s": float,
                "txcmp/s": float,
                "rxmcst/s": float,
                r"%ifutil": float,
            }
        )
        return self.filter_dataframe(self.sar_data[sar_loc], data_type).astype(astype_t)

    def get_network_statistics_avg(self, on_failures: bool = False):
        return (
            self.get_network_statistics(data_type="average", on_failures=on_failures)
            .drop(columns=["timestamp"])
            .to_dict(orient="records")
        )

    def get_memory_usage(self, data_type: str = "detail"):
        """
        Returns the memory usage data.

        Args:
            data_type (str, optional): The type of memory usage data to retrieve. Defaults to "detail".

        Returns:
            pd.DataFrame: Dataframe containing the memory usage data.
        """
        return self.filter_dataframe(self.sar_data[6], data_type).astype(
            {
                "kbmemfree": int,
                "kbavail": int,
                "kbmemused": int,
                r"%memused": float,
                "kbbuffers": int,
                "kbcached": int,
                "kbcommit": int,
                r"%commit": float,
                "kbactive": int,
                "kbinact": int,
                "kbdirty": int,
                "kbanonpg": int,
                "kbslab": int,
                "kbkstack": int,
                "kbpgtbl": int,
                "kbvmused": int,
            }
        )

    def get_memory_usage_avg(self):
        """
        Returns the average memory usage data.

        Returns:
            dict: A dictionary containing the average memory usage data.
        """
        return (
            self.get_memory_usage("average")
            .drop(columns=["timestamp"])
            .to_dict(orient="records")[0]
        )

    def plot_memory_usage(self):
        """
        Plots the memory usage over time.
        """
        df = self.get_memory_usage()
        df = trans_time_to_seconds(df)
        sns.lineplot(data=df, x="timestamp", y=r"%memused")

    def get_disk_usage(self, dev: str = None, data_type: str = "detail"):
        """
        Returns the disk usage data.

        Args:
            data_type (str, optional): The type of disk usage data to retrieve. Defaults to "detail".

        Returns:
            pd.DataFrame: Dataframe containing the disk usage data.
        """
        df = self.filter_dataframe(self.sar_data[11], data_type).astype(
            {
                "tps": "float64",
                r"rkB/s": "float64",
                r"wkB/s": "float64",
                r"dkB/s": "float64",
                "areq-sz": "float64",
                "aqu-sz": "float64",
                "await": "float64",
                r"%util": "float64",
            }
        )
        return df[df["DEV"] == dev] if dev else df

    def get_disk_usage_avg(self, dev: str = None):
        """
        Returns the average disk usage data.

        Args:
            dev (str, optional): The disk device to retrieve the average data for. Defaults to None.

        Returns:
            list: A list of dictionaries containing the average disk usage data for each device.
            if dev is specified, returns a single dictionary.
        """
        disk_usage_avg = (
            self.get_disk_usage(dev, "average")
            .drop(columns=["timestamp"])
            .rename(columns={"%util": "%disk_util", "await": "disk_await"})
            .to_dict(orient="records")
        )
        return disk_usage_avg[0] if dev else disk_usage_avg

    def plot_disk_usage(self, dev: str = None, metrics="tps"):
        """
        Plots the disk tps over time.
        """
        df = self.get_disk_usage()
        df = trans_time_to_seconds(df).query(f"DEV=='{dev}'") if dev else df
        if dev:
            sns.lineplot(data=df, x="timestamp", y=metrics)
        else:
            sns.lineplot(data=df, x="timestamp", y=metrics, hue="DEV")


def parse_sar_bin_to_txt(sar_bin_path: str):
    """
    Parses the SAR binary file into a list of lines.

    Args:
        sar_bin_path (str): Path to the SAR binary file.

    Returns:
        list: List of lines in the SAR binary file.
    """
    sar_lines = run_command(f"LC_ALL='C' sar -A -f {sar_bin_path}").split("\n")
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


def trans_time_to_seconds(df):
    """
    Transforms the timestamp column in the given DataFrame to seconds.

    Args:
        df (pandas.DataFrame): The DataFrame containing the timestamp column.

    Returns:
        pandas.DataFrame: The DataFrame with the timestamp column transformed to seconds.
    """
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%H:%M:%S")
    df["timestamp"] -= df.loc[:, "timestamp"].iloc[0]
    df["timestamp"] = df["timestamp"].dt.total_seconds()
    return df


def merge_one_line(sar_line: str) -> list:
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


def add_post_fix(sar_line: list, len_columns: int):
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


def process_subtable(
    sar_columns: list, sar_blocks: list, processes_num=min(12, NUM_CORES_PHYSICAL)
):
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
        return [add_post_fix(merge_one_line(x), len(sar_columns)) for x in sar_blocks]
    pool = multiprocessing.Pool(processes=processes_num)
    merged_lines = pool.map(merge_one_line, sar_blocks)
    res = pool.starmap(
        add_post_fix,
        zip(merged_lines, [len(sar_columns) for _ in range(len(merged_lines))]),
    )
    pool.close()
    pool.join()
    return res


def sar_to_df(sar_blocks: list):
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
        process_subtable(sar_columns, sar_blocks[1:]),
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
    a = [sar_to_df(d) for d in sar_data]
    l = 0
    res = []
    while l < len(a):  # merge dataframes with the same columns, use two pointers
        r = l + 1
        while r < len(a) and a[r].columns.equals(a[l].columns):
            r += 1
        res.append(pd.concat(a[l:r], axis=0))
        l = r
    return res
