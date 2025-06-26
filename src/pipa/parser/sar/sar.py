import pandas as pd
import seaborn as sns
import re
from pipa.common.cmd import run_command
from pipa.common.hardware.cpu import NUM_CORES_PHYSICAL
from pipa.common.logger import logger
from pipa.common.utils import generate_unique_rgb_color
from .sar_index import SarDataIndex
from typing import Optional, Dict, List, Literal
import multiprocessing
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pipa.parser import make_single_plot


class SarData:
    def __init__(self, sar_string: str):
        """
        Initialize a SAR object with the given SAR string.

        Args:
            sar_string (str): The SAR string to parse.

        """
        self.sar_data: list[pd.DataFrame] = parse_sar_string(sar_string)
        self.saridx_2_colidx: Dict[SarDataIndex, int] = {}
        for i, sard in enumerate(self.sar_data):
            scolumns = sard.columns.to_list()
            sindex = SarDataIndex.contains(scolumns)
            if sindex:
                self.saridx_2_colidx[sindex] = i
            else:
                logger.warning(
                    f"{scolumns} not supported in pipa sar parse, please report an issue"
                )
        for sindex in self.saridx_2_colidx.keys():
            all_m = SarDataIndex.avg_metric_to_all_metric(sindex)
            if all_m and all_m in self.saridx_2_colidx:
                all_m_i = self.saridx_2_colidx[all_m]
                sindex_i = self.saridx_2_colidx[sindex]
                avg_pd = self.sar_data[sindex_i]
                avg_pd = avg_pd.rename(columns={"Average:": "timestamp"})
                self.sar_data[all_m_i] = (
                    pd.concat([self.sar_data[all_m_i], avg_pd])
                    .drop_duplicates()
                    .reset_index(drop=True)
                )
                logger.debug(f"combine avg metric {sindex} to all metric {all_m}")

    def get_column_index(self, sar_index: SarDataIndex) -> Optional[int]:
        return self.saridx_2_colidx.get(sar_index)

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
        idx = self.get_column_index(SarDataIndex.CPUUtils)
        if idx is None:
            raise KeyError(f"{SarDataIndex.CPUUtils} not found in sar data")
        util = self.filter_dataframe(self.sar_data[idx], data_type).astype(
            SarDataIndex.CPUUtilsMetrics.value
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

    def plot_interactive_CPU_metrics(
        self,
        threads: Optional[list[int]] = None,
        metrics: List[
            Literal[
                r"%usr",
                r"%nice",
                r"%sys",
                r"%iowait",
                r"%irq",
                r"%soft",
                r"%steal",
                r"%guest",
                r"%gnice",
                r"%idle",
                r"%util",
            ]
        ] = [r"%util"],
        aggregation: bool = False,
        raw_data: bool = False,
        show: bool = True,
        write_to_html: Optional[str] = None,
    ) -> List[go.Scatter] | go.Figure:
        """Plots interactive CPU metrics over time.

        You can generate your own plotly fig from returned scatters when raw_data is True. Else will generate figure and return it.

        Args:
            threads (Optional[list[int]], optional): Specify cpu to show in fig. Defaults to None.
                When in aggregation mode, none means all, otherwise aggregate select threads.
                When in non-aggregation mode, none means display all cpu threads, otherwise display selected threads.
            metrics (List[ Literal[ r, optional): The CPU metrics to show. Defaults to [r"%util"].
            aggregation (bool, optional): Whether to aggregate the data by CPU thread. Defaults to False.

        Returns:
            List[go.Scatter]: list of raw CPU metrics scatters.
        """
        df = self.get_CPU_utilization()
        # minus 'all'
        cpu_counts = df["CPU"].nunique() - 1
        df = trans_time_to_seconds(df)
        scatters = []
        if aggregation:
            if threads:
                df = df[df["CPU"].isin([str(t) for t in threads])]
                df = df.groupby("timestamp").mean(numeric_only=True).reset_index()
                df["CPU"] = "all"
            threads = ["all"]
        elif threads is None:
            threads = list(range(0, cpu_counts))
        for t in threads:
            cpu_data = df[df["CPU"] == str(t)]
            for i, y in enumerate(metrics):
                r, g, b = generate_unique_rgb_color([t, i], generate_seed=True)
                try:
                    scatters.append(
                        go.Scatter(
                            x=cpu_data["timestamp"],
                            y=cpu_data[y],
                            mode="lines+markers",
                            name=f"CPU {t} {y}",
                            # different colors
                            line=dict(color=f"rgb({r}, {g}, {b})"),
                        )
                    )
                except KeyError as e:
                    logger.warning(
                        f"metric {y} not found in columns {cpu_data.columns.to_list()}: {e}"
                    )
        if raw_data:
            return scatters
        else:
            return make_single_plot(
                scatters=scatters,
                title="CPU Metrics Trend",
                xaxis_title="Timestamp",
                yaxis_title="Percentage",
                show=show,
                write_to_html=write_to_html,
            )

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
        idx = self.get_column_index(SarDataIndex.CPUFreq)
        if idx is None:
            raise KeyError(f"{SarDataIndex.CPUFreq} not found in sar data")
        return self.filter_dataframe(self.sar_data[idx], data_type).astype(
            {"MHz": "float64"}
        )

    def plot_interactive_CPU_freq(
        self,
        threads: Optional[list[int]] = None,
        aggregation: bool = False,
        raw_data: bool = False,
        show: bool = True,
        write_to_html: Optional[str] = None,
    ) -> List[go.Scatter] | go.Figure:
        """
        Plot raw scatters of CPU frequency metrics over time.

        You can generate the fig from returned scatters when raw_data is True. Else will generate figure and return it.

        Args:
            threads (Optional[list[int]], optional): CPU threads. Defaults to None, means choose 'all' CPU thread.

        Returns:
            List[go.Scatter]: list of raw scatter plots.
        """
        df = self.get_CPU_frequency()
        # minus 'all'
        cpu_counts = df["CPU"].nunique() - 1
        df = trans_time_to_seconds(df)
        scatters = []
        if aggregation:
            if threads:
                df = df[df["CPU"].isin([str(t) for t in threads])]
                df = df.groupby("timestamp").mean(numeric_only=True).reset_index()
                df["CPU"] = "all"
            threads = ["all"]
        elif threads is None:
            threads = list(range(0, cpu_counts))
        for t in threads:
            cpu_data = df[df["CPU"] == str(t)]
            r, g, b = generate_unique_rgb_color([t], generate_seed=True)
            scatters.append(
                go.Scatter(
                    x=cpu_data["timestamp"],
                    y=cpu_data["MHz"],
                    mode="lines+markers",
                    name=f"CPU {t} Freq",
                    # different colors
                    line=dict(color=f"rgb({r}, {g}, {b})"),
                )
            )
        if raw_data:
            return scatters
        else:
            return make_single_plot(
                scatters=scatters,
                title="CPU Freq Trend",
                xaxis_title="Timestamp",
                yaxis_title="MHz",
                show=show,
                write_to_html=write_to_html,
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
        """Get network statistics

        Args:
            data_type (str, optional): detail / raw / average. Defaults to "detail".
            on_failures (bool, optional): use NetError if true, else using NetStat. Defaults to False.

        Returns:
            pd.DataFrame: Dataframe containing the Network Stattistics data.
        """
        sar_loc = SarDataIndex.NetError if on_failures else SarDataIndex.NetUtils
        idx = self.get_column_index(sar_loc)
        if idx is None:
            raise KeyError(f"{sar_loc} not found in sar data")
        astype_t = (
            SarDataIndex.NetErrorMetrics.value
            if on_failures
            else SarDataIndex.NetUtilsMetrics.value
        )
        return self.filter_dataframe(self.sar_data[idx], data_type).astype(astype_t)

    def plot_interactive_network_stat(
        self,
        devs: list[str],
        trans_metrics: List[
            Literal[
                "rxpck/s",
                "txpck/s",
                "rxkB/s",
                "txkB/s",
                "rxcmp/s",
                "txcmp/s",
                "rxmcst/s",
                r"%ifutil",
            ]
        ] = [r"%ifutil"],
        err_metrics: List[
            Literal[
                "rxerr/s",
                "txerr/s",
                "coll/s",
                "rxdrop/s",
                "rxdrop/s",
                "txcarr/s",
                "rxfram/s",
                "rxfifo/s",
                "txfifo/s",
            ]
        ] = [r"rxerr/s"],
        on_failures=False,
        raw_data: bool = False,
        show: bool = True,
        write_to_html: Optional[str] = None,
    ) -> List[go.Scatter] | go.Figure:
        """
        Plots interactive network statistics over time.

        This function generates an interactive time series for the specified network devices and metrics.
        It can plot either transmission metrics or error metrics based on the `on_failures` flag.
        You can generate your own plotly fig from returned scatters when raw_data is True. Else will generate figure and return it.

        Args:
            devs (list[str]): A list of network device names to include in the plot.
            trans_metrics (List[Literal], optional): A list of transmission metrics to plot. Defaults to `["%ifutil"]`.
            err_metrics (List[Literal], optional): A list of error metrics to plot. Defaults to `["rxerr/s"]`.
            on_failures (bool, optional): If True, plots error metrics; otherwise, plots transmission metrics. Defaults to False.

        Returns:
            List[go.Scatter]: A list of Plotly Scatter objects representing the time series data for each device and metric.
        """
        if len(devs) < 1:
            return []
        metrics = err_metrics if on_failures else trans_metrics
        df = self.get_network_statistics(on_failures=on_failures)
        df = trans_time_to_seconds(df)

        scatters = []
        for t in devs:
            dev_data = df[df["IFACE"] == t]
            for i, y in enumerate(metrics):
                r, g, b = generate_unique_rgb_color([t, i], generate_seed=True)
                try:
                    scatters.append(
                        go.Scatter(
                            x=dev_data["timestamp"],
                            y=dev_data[y],
                            mode="lines+markers",
                            name=f"IFACE {t} {y}",
                            # different colors
                            line=dict(color=f"rgb({r}, {g}, {b})"),
                        )
                    )
                except KeyError as e:
                    logger.warning(
                        f"metric {y} not found in columns {dev_data.columns.to_list()}: {e}"
                    )
        if raw_data:
            return scatters
        else:
            return make_single_plot(
                scatters=scatters,
                title="Net Err Trend" if on_failures else "Net Stat Trend",
                xaxis_title="Timestamp",
                yaxis_title="Net Stat",
                show=show,
                write_to_html=write_to_html,
            )

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
        idx = self.get_column_index(SarDataIndex.MemoryStats)
        if idx is None:
            raise KeyError(f"{SarDataIndex.MemoryStats} not found in sar data")
        return self.filter_dataframe(self.sar_data[idx], data_type).astype(
            SarDataIndex.MemoryStatsMetrics.value
        )

    def plot_interactive_mem_usage(
        self,
        metrics: List[
            Literal[
                "kbmemfree",
                "kbavail",
                "kbmemused",
                r"%memused",
                "kbbuffers",
                "kbcached",
                "kbcommit",
                r"%commit",
                "kbactive",
                "kbinact",
                "kbdirty",
                "kbanonpg",
                "kbslab",
                "kbkstack",
                "kbpgtbl",
                "kbvmused",
            ]
        ] = [r"%memused"],
        raw_data: bool = False,
        show: bool = True,
        write_to_html: Optional[str] = None,
    ) -> List[go.Scatter] | go.Figure:
        """
        Generates interactive memory usage time series plots.

        This function generates the time series data for the specified memory metrics.
        Each metric is plotted with a unique color.
        You can generate your own plotly fig from returned scatters when raw_data is True. Else will generate figure and return it.

        Args:
            metrics (List[Literal], optional): A list of memory metrics to plot. Defaults to `["%memused"]`.

        Returns:
            List[go.Scatter]: A list of Plotly Scatter objects representing the time series data for each memory metric.
        """
        df = self.get_memory_usage()
        df = trans_time_to_seconds(df)

        scatters = []
        for i, y in enumerate(metrics):
            r, g, b = generate_unique_rgb_color([i], generate_seed=True)
            try:
                scatters.append(
                    go.Scatter(
                        x=df["timestamp"],
                        y=df[y],
                        mode="lines+markers",
                        name=f"memory {y}",
                        # different colors
                        line=dict(color=f"rgb({r}, {g}, {b})"),
                    )
                )
            except KeyError as e:
                logger.warning(
                    f"metric {y} not found in columns {df.columns.to_list()}: {e}"
                )
        if raw_data:
            return scatters
        else:
            return make_single_plot(
                scatters=scatters,
                title="Memory Metrics Trend",
                xaxis_title="Timestamp",
                yaxis_title="Memory Usage",
                show=show,
                write_to_html=write_to_html,
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
        idx = self.get_column_index(SarDataIndex.DeviceIOStats)
        if idx is None:
            raise KeyError(f"{SarDataIndex.DeviceIOStats} not found in sar data")
        df = self.filter_dataframe(self.sar_data[idx], data_type).astype(
            SarDataIndex.DeviceIOStatsMetrics.value
        )
        return df[df["DEV"] == dev] if dev else df

    def plot_interactive_disk_usage(
        self,
        devs: list[str],
        metrics: List[
            Literal[
                "tps",
                r"rkB/s",
                r"wkB/s",
                r"dkB/s",
                "areq-sz",
                "aqu-sz",
                "await",
                r"%util",
            ]
        ] = [r"%util"],
        raw_data: bool = False,
        show: bool = True,
        write_to_html: Optional[str] = None,
    ) -> List[go.Scatter] | go.Figure:
        """
        Generates interactive disk usage time series plots.

        This function generates the time series data for the specified disk devices and metrics.
        Each metric for each device is plotted with a unique color.
        You can generate your own plotly fig from returned scatters when raw_data is True. Else will generate figure and return it.

        Args:
            devs (list[str]): A list of disk device names to include in the plot.
            metrics (List[Literal], optional): A list of disk usage metrics to plot. Defaults to `["%util"]`.

        Returns:
            List[go.Scatter]: A list of Plotly Scatter objects representing the time series data for each disk device and metric.
        """
        if len(devs) < 1:
            return []
        df = self.get_disk_usage()
        df = trans_time_to_seconds(df)

        scatters = []
        for t in devs:
            cpu_data = df[df["DEV"] == t]
            for i, y in enumerate(metrics):
                r, g, b = generate_unique_rgb_color([t, i], generate_seed=True)
                try:
                    scatters.append(
                        go.Scatter(
                            x=cpu_data["timestamp"],
                            y=cpu_data[y],
                            mode="lines+markers",
                            name=f"DEV {t} {y}",
                            # different colors
                            line=dict(color=f"rgb({r}, {g}, {b})"),
                        )
                    )
                except KeyError as e:
                    logger.warning(
                        f"metric {y} not found in columns {cpu_data.columns.to_list()}: {e}"
                    )
        if raw_data:
            return scatters
        else:
            return make_single_plot(
                scatters=scatters,
                title="Disk Usage Trend",
                xaxis_title="Timestamp",
                yaxis_title="Disk Usage",
                show=show,
                write_to_html=write_to_html,
            )

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
        df = trans_time_to_seconds(df)
        df = df.query(f"DEV=='{dev}'") if dev else df
        if dev:
            sns.lineplot(data=df, x="timestamp", y=metrics)
        else:
            sns.lineplot(data=df, x="timestamp", y=metrics, hue="DEV")

    def plot_all_metrics(
        self,
        net_devs: list[str],
        disk_devs: list[str],
        cpu_threads: Optional[list[int]] = None,
        cpu_metrics: List[
            Literal[
                r"%usr",
                r"%nice",
                r"%sys",
                r"%iowait",
                r"%irq",
                r"%soft",
                r"%steal",
                r"%guest",
                r"%gnice",
                r"%idle",
                r"%util",
            ]
        ] = [r"%util"],
        cpu_aggregation: bool = False,
        net_trans_metrics: List[
            Literal[
                "rxpck/s",
                "txpck/s",
                "rxkB/s",
                "txkB/s",
                "rxcmp/s",
                "txcmp/s",
                "rxmcst/s",
                r"%ifutil",
            ]
        ] = [r"%ifutil"],
        net_err_metrics: List[
            Literal[
                "rxerr/s",
                "txerr/s",
                "coll/s",
                "rxdrop/s",
                "rxdrop/s",
                "txcarr/s",
                "rxfram/s",
                "rxfifo/s",
                "txfifo/s",
            ]
        ] = [r"rxerr/s"],
        mem_metrics: List[
            Literal[
                "kbmemfree",
                "kbavail",
                "kbmemused",
                r"%memused",
                "kbbuffers",
                "kbcached",
                "kbcommit",
                r"%commit",
                "kbactive",
                "kbinact",
                "kbdirty",
                "kbanonpg",
                "kbslab",
                "kbkstack",
                "kbpgtbl",
                "kbvmused",
            ]
        ] = [r"%memused"],
        disk_metrics: List[
            Literal[
                "tps",
                r"rkB/s",
                r"wkB/s",
                r"dkB/s",
                "areq-sz",
                "aqu-sz",
                "await",
                r"%util",
            ]
        ] = [r"%util"],
        show: bool = True,
        write_to_html: Optional[str] = None,
        height=1000,
        shared_xaxes=True,
        vertical_spacing=0.1,
    ):
        """
        Plots comprehensive system metrics including CPU utilization, CPU frequency, network transmission, network errors, memory usage, and disk usage.

        This function generates an interactive plot with multiple subplots, each representing a different system metric. The plot can be displayed and optionally saved as an HTML file.

        Args:
            net_devs (list[str]): A list of network device names to include in the plot.
            disk_devs (list[str]): A list of disk device names to include in the plot.
            cpu_threads (Optional[list[int]], optional): A list of CPU thread IDs to include in the CPU metrics. Defaults to None.
            cpu_metrics (List[Literal], optional): A list of CPU metrics to plot. Defaults to `["%util"]`.
            cpu_aggregation (bool, optional): Whether to aggregate CPU metrics across all threads. Defaults to False.
            net_trans_metrics (List[Literal], optional): A list of network transmission metrics to plot. Defaults to `["%ifutil"]`.
            net_err_metrics (List[Literal], optional): A list of network error metrics to plot. Defaults to `["rxerr/s"]`.
            mem_metrics (List[Literal], optional): A list of memory metrics to plot. Defaults to `["%memused"]`.
            disk_metrics (List[Literal], optional): A list of disk usage metrics to plot. Defaults to `["%util"]`.
            show (bool, optional): Whether to show the plot. Defaults to True
            write_to_html (Optional[str], optional): The filename to save the plot as an HTML file. If None, the plot is not saved. Defaults to None.
            height (int, optional): The height of the plot in pixels. Defaults to 1000.
            shared_xaxes (bool, optional): Whether to share the x-axis across subplots. Defaults to True.
            vertical_spacing (float, optional): The vertical spacing between subplots. Defaults to 0.1.
        """
        cpu_util_scatters = self.plot_interactive_CPU_metrics(
            threads=cpu_threads,
            metrics=cpu_metrics,
            aggregation=cpu_aggregation,
            raw_data=True,
        )
        cpu_freq_scatters = self.plot_interactive_CPU_freq(
            threads=cpu_threads, raw_data=True
        )
        net_trans_scatters = self.plot_interactive_network_stat(
            on_failures=False,
            devs=net_devs,
            trans_metrics=net_trans_metrics,
            raw_data=True,
        )
        net_err_scatters = self.plot_interactive_network_stat(
            on_failures=True, devs=net_devs, err_metrics=net_err_metrics, raw_data=True
        )
        mem_scatters = self.plot_interactive_mem_usage(
            metrics=mem_metrics, raw_data=True
        )
        disk_scatters = self.plot_interactive_disk_usage(
            devs=disk_devs, metrics=disk_metrics, raw_data=True
        )
        # subtitle: scatters, x_title, y_title
        all_scatters = {
            "CPU Utilization": (cpu_util_scatters, "timestamp", "Percentage"),
            "CPU Frequency": (cpu_freq_scatters, "timestamp", "MHz"),
            "Network Transmission": (net_trans_scatters, "timestamp", "Net Stat"),
            "Network Error": (net_err_scatters, "timestamp", "Net Stat"),
            "Memory Usage": (mem_scatters, "timestamp", "Memory Usage"),
            "Disk Usage": (disk_scatters, "timestamp", "Disk Usage"),
        }
        rows = 0
        sub_titles = []
        exist_scatters = {}
        for k, v in all_scatters.items():
            s, _, _ = v
            if len(s) > 0:
                rows += 1
                sub_titles.append(k)
                # scatters, x_title, y_title
                exist_scatters[k] = v
        fig = make_subplots(
            rows=rows,
            cols=1,
            subplot_titles=sub_titles,
            # Share same x axis since all is timestamp
            shared_xaxes=shared_xaxes,
            vertical_spacing=vertical_spacing,
        )
        for i, (_, v) in enumerate(exist_scatters.items()):
            s, xt, yt = v
            for scatter in s:
                fig.add_trace(scatter, row=i + 1, col=1)
            fig.update_xaxes(title_text=xt, row=i + 1, col=1)
            fig.update_yaxes(title_text=yt, row=i + 1, col=1)
        fig.update_layout(
            title="System Metrics Trends",
            hovermode="closest",
            height=height,
            showlegend=True,
        )
        if show:
            fig.show()
        if write_to_html:
            fig.write_html(write_to_html)
        return fig


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


def trans_time_to_seconds(df: pd.DataFrame):
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
        result.append(base_date + pd.Timedelta(days=day_prefix) + pd.to_timedelta(ts))
    df["timestamp"] = result

    try:
        df["timestamp"] -= df.loc[:, "timestamp"].iloc[0]
        df["timestamp"] = df["timestamp"].dt.total_seconds()
    except IndexError as e:
        logger.warning(
            f"{df.columns.to_list()} column may has wrong format, please check the origin sar data"
        )
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
