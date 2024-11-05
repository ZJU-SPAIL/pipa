import pandas as pd
import seaborn as sns
import re
import random
from pipa.common.cmd import run_command
from pipa.common.hardware.cpu import NUM_CORES_PHYSICAL
from pipa.common.logger import logger
from pipa.common.utils import generate_unique_rgb_color
from enum import Enum, unique
from typing import Optional, Dict, List, Literal
import multiprocessing
import plotly.graph_objects as go
from plotly.subplots import make_subplots


@unique
class SarDataIndex(Enum):
    CPUUtils = [
        "timestamp",
        "CPU",
        r"%usr",
        r"%nice",
        r"%sys",
        r"%iowait",
        r"%steal",
        r"%irq",
        r"%soft",
        r"%guest",
        r"%gnice",
        r"%idle",
    ]
    AvgCPUUtils = [
        "Average:",
        "CPU",
        r"%usr",
        r"%nice",
        r"%sys",
        r"%iowait",
        r"%steal",
        r"%irq",
        r"%soft",
        r"%guest",
        r"%gnice",
        r"%idle",
    ]
    CPUPressureStats = ["timestamp", r"%scpu-10", r"%scpu-60", r"%scpu-300", r"%scpu"]
    ProcessStats = [
        "timestamp",
        "proc/s",
        "cswch/s",
    ]
    AvgInterruptStats = ["Average:", "INTR", "intr/s"]
    InterruptStats = [
        "timestamp",
        "INTR",
        "intr/s",
    ]
    SwapStats = [
        "timestamp",
        "pswpin/s",
        "pswpout/s",
    ]
    PagingStats = [
        "timestamp",
        "pgpgin/s",
        "pgpgout/s",
        "fault/s",
        "majflt/s",
        "pgfree/s",
        "pgscank/s",
        "pgscand/s",
        "pgsteal/s",
        r"%vmeff",
    ]
    DiskIOStats = [
        "timestamp",
        "tps",
        "rtps",
        "wtps",
        "dtps",
        "bread/s",
        "bwrtn/s",
        "bdscd/s",
    ]
    MemPressureStats = [
        "timestamp",
        r"%smem-10",
        r"%smem-60",
        r"%smem-300",
        r"%smem",
        r"%fmem-10",
        r"%fmem-60",
        r"%fmem-300",
        r"%fmem",
    ]
    MemoryStats = [
        "timestamp",
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
    SwapMemoryStats = [
        "timestamp",
        "kbswpfree",
        "kbswpused",
        r"%swpused",
        "kbswpcad",
        r"%swpcad",
    ]
    HugePagesStats = [
        "timestamp",
        "kbhugfree",
        "kbhugused",
        r"%hugused",
        "kbhugrsvd",
        "kbhugsurp",
    ]
    FileSystemStats = [
        "timestamp",
        "dentunusd",
        "file-nr",
        "inode-nr",
        "pty-nr",
    ]
    LoadStats = [
        "timestamp",
        "runq-sz",
        "plist-sz",
        "ldavg-1",
        "ldavg-5",
        "ldavg-15",
        "blocked",
    ]
    TTYStats = [
        "timestamp",
        "TTY",
        "rcvin/s",
        "xmtin/s",
        "framerr/s",
        "prtyerr/s",
        "brk/s",
        "ovrun/s",
    ]
    IOPressureStats = [
        "timestamp",
        r"%sio-10",
        r"%sio-60",
        r"%sio-300",
        r"%sio",
        r"%fio-10",
        r"%fio-60",
        r"%fio-300",
        r"%fio",
    ]
    DeviceIOStats = [
        "timestamp",
        "DEV",
        "tps",
        "rkB/s",
        "wkB/s",
        "dkB/s",
        "areq-sz",
        "aqu-sz",
        "await",
        r"%util",
    ]
    NetUtils = [
        "timestamp",
        "IFACE",
        "rxpck/s",
        "txpck/s",
        "rxkB/s",
        "txkB/s",
        "rxcmp/s",
        "txcmp/s",
        "rxmcst/s",
        r"%ifutil",
    ]
    NetError = [
        "timestamp",
        "IFACE",
        "rxerr/s",
        "txerr/s",
        "coll/s",
        "rxdrop/s",
        "txdrop/s",
        "txcarr/s",
        "rxfram/s",
        "rxfifo/s",
        "txfifo/s",
    ]
    NFSClientStats = [
        "timestamp",
        "call/s",
        "retrans/s",
        "read/s",
        "write/s",
        "access/s",
        "getatt/s",
    ]
    NFSServerStats = [
        "timestamp",
        "scall/s",
        "badcall/s",
        "packet/s",
        "udp/s",
        "tcp/s",
        "hit/s",
        "miss/s",
        "sread/s",
        "swrite/s",
        "saccess/s",
        "sgetatt/s",
    ]
    SocketStats = [
        "timestamp",
        "totsck",
        "tcpsck",
        "udpsck",
        "rawsck",
        "ip-frag",
        "tcp-tw",
    ]
    IPStats = [
        "timestamp",
        "irec/s",
        "fwddgm/s",
        "idel/s",
        "orq/s",
        "asmrq/s",
        "asmok/s",
        "fragok/s",
        "fragcrt/s",
    ]
    IPErrorStats = [
        "timestamp",
        "ihdrerr/s",
        "iadrerr/s",
        "iukwnpr/s",
        "idisc/s",
        "odisc/s",
        "onort/s",
        "asmf/s",
        "fragf/s",
    ]
    ICMPStats = [
        "timestamp",
        "imsg/s",
        "omsg/s",
        "iech/s",
        "iechr/s",
        "oech/s",
        "oechr/s",
        "itm/s",
        "itmr/s",
        "otm/s",
        "otmr/s",
        "iadrmk/s",
        "iadrmkr/s",
        "oadrmk/s",
        "oadrmkr/s",
    ]
    ICMPErrorStats = [
        "timestamp",
        "ierr/s",
        "oerr/s",
        "idstunr/s",
        "odstunr/s",
        "itmex/s",
        "otmex/s",
        "iparmpb/s",
        "oparmpb/s",
        "isrcq/s",
        "osrcq/s",
        "iredir/s",
        "oredir/s",
    ]
    TCPStats = [
        "timestamp",
        "active/s",
        "passive/s",
        "iseg/s",
        "oseg/s",
    ]
    TCPExtStats = [
        "timestamp",
        "atmptf/s",
        "estres/s",
        "retrans/s",
        "isegerr/s",
        "orsts/s",
    ]
    UDPStats = [
        "timestamp",
        "idgm/s",
        "odgm/s",
        "noport/s",
        "idgmerr/s",
    ]
    IPv6SocketStats = [
        "timestamp",
        "tcp6sck",
        "udp6sck",
        "raw6sck",
        "ip6-frag",
    ]
    IPv6Stats = [
        "timestamp",
        "irec6/s",
        "fwddgm6/s",
        "idel6/s",
        "orq6/s",
        "asmrq6/s",
        "asmok6/s",
        "imcpck6/s",
        "omcpck6/s",
        "fragok6/s",
        "fragcr6/s",
    ]
    IPv6ErrorStats = [
        "timestamp",
        "ihdrer6/s",
        "iadrer6/s",
        "iukwnp6/s",
        "i2big6/s",
        "idisc6/s",
        "odisc6/s",
        "inort6/s",
        "onort6/s",
        "asmf6/s",
        "fragf6/s",
        "itrpck6/s",
    ]
    ICMPv6Stats = [
        "timestamp",
        "imsg6/s",
        "omsg6/s",
        "iech6/s",
        "iechr6/s",
        "oechr6/s",
        "igmbq6/s",
        "igmbr6/s",
        "ogmbr6/s",
        "igmbrd6/s",
        "ogmbrd6/s",
        "irtsol6/s",
        "ortsol6/s",
        "irtad6/s",
        "inbsol6/s",
        "onbsol6/s",
        "inbad6/s",
        "onbad6/s",
    ]
    ICMPv6ErrorStats = [
        "timestamp",
        "ierr6/s",
        "idtunr6/s",
        "odtunr6/s",
        "itmex6/s",
        "otmex6/s",
        "iprmpb6/s",
        "oprmpb6/s",
        "iredir6/s",
        "oredir6/s",
        "ipck2b6/s",
        "opck2b6/s",
    ]
    UDPv6Stats = [
        "timestamp",
        "idgm6/s",
        "odgm6/s",
        "noport6/s",
        "idgmer6/s",
    ]
    AvgSoftNetStats = [
        "Average:",
        "CPU",
        "total/s",
        "dropd/s",
        "squeezd/s",
        "rx_rps/s",
        "flw_lim/s",
    ]
    SoftNetStats = [
        "timestamp",
        "CPU",
        "total/s",
        "dropd/s",
        "squeezd/s",
        "rx_rps/s",
        "flw_lim/s",
    ]
    AvgCPUFreq = ["Average:", "CPU", "MHz"]
    CPUFreq = ["timestamp", "CPU", "MHz"]
    TemperatureStats = [
        "timestamp",
        "TEMP",
        "degC",
        r"%temp",
        "DEVICE",
    ]
    BusStats = [
        "timestamp",
        "BUS",
        "idvendor",
        "idprod",
        "maxpower",
        "manufact",
        "product",
    ]
    FileSystemSpaceStats = [
        "timestamp",
        "MBfsfree",
        "MBfsused",
        r"%fsused",
        r"%ufsused",
        "Ifree",
        "Iused",
        r"%Iused",
        "FILESYSTEM",
    ]

    @classmethod
    def contains(cls, item) -> Optional[Enum]:
        for k in cls:
            if item == k.value:
                return k
        return None

    @classmethod
    def avg_metric_to_all_metric(cls, item: Enum) -> Optional[Enum]:
        match item:
            case cls.AvgCPUUtils:
                return cls.CPUUtils
            case cls.AvgInterruptStats:
                return cls.InterruptStats
            case cls.AvgCPUFreq:
                return cls.CPUFreq
            case cls.AvgSoftNetStats:
                return cls.SoftNetStats
            case _:
                return None

    def __eq__(self, value: object) -> bool:
        return self.value == value

    def __hash__(self) -> int:
        return hash(self.name)


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

    def plot_interactive_CPU_metrics_time_raw(
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
    ) -> List[go.Scatter]:
        """Plots interactive CPU metrics over time. Get raw plotly data

        You can generate your own plotly pic from these scatters.

        Args:
            threads (Optional[list[int]], optional): Specify cpu threads. Defaults to None, means just select 'all' CPU thread.
            metrics (List[ Literal[ r, optional): The CPU metrics to show. Defaults to [r"%util"].

        Returns:
            List[go.Scatter]: list of raw CPU metrics scatters.
        """
        df = self.get_CPU_utilization()
        df = (
            df[df["CPU"].isin([str(t) for t in threads])]
            if threads
            else df.query("CPU=='all'")
        )
        df = trans_time_to_seconds(df)

        scatters = []
        if threads:
            for t in threads:
                cpu_data = df[df["CPU"] == str(t)]
                for i, y in enumerate(metrics):
                    seed = random.randint(1, 256)
                    r, g, b = generate_unique_rgb_color([t, i, seed])
                    scatters.append(
                        go.Scatter(
                            x=cpu_data["timestamp"],
                            y=cpu_data[y],
                            mode="lines+markers",
                            name=f"CPU{t} {y}",
                            # different colors
                            line=dict(color=f"rgb({r}, {g}, {b})"),
                        )
                    )
        else:
            for i, y in enumerate(metrics):
                seed = random.randint(1, 256)
                r, g, b = generate_unique_rgb_color([i, seed])
                scatters.append(
                    go.Scatter(
                        x=df["timestamp"],
                        y=df[y],
                        mode="lines+markers",
                        name=f"CPU All {y}",
                        # different colors
                        line=dict(color=f"rgb({r}, {g}, {b})"),
                    )
                )
        return scatters

    def plot_interactive_CPU_metrics_time(
        self,
        threads: Optional[List[int]] = None,
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
        write_html_name: Optional[str] = None,
    ):
        """
        Plot interactive CPU metrics over time.

        This function generates an interactive chart showing the trends of specified CPU metrics over time.
        It can optionally save the chart as an HTML file.

        Args:
            threads (Optional[List[int]], optional): List of thread numbers to be displayed. Defaults to None, which means displaying all threads.
            metrics (List[Literal[...]], optional): List of CPU metrics to be displayed. Defaults to ["%util"].
            write_html_name (Optional[str], optional): Name of the HTML file to be saved. Defaults to None, which means not saving the file.
        """
        scatters = self.plot_interactive_CPU_metrics_time_raw(threads, metrics)
        fig = go.Figure()
        for s in scatters:
            fig.add_trace(s)
        fig.update_layout(
            title="CPU Metrics Trend",
            xaxis_title="Timestamp",
            yaxis_title="Percentage",
            hovermode="closest",
            updatemenus=[
                {
                    "direction": "left",
                    "pad": {"r": 10, "t": 87},
                    "showactive": False,
                    "type": "buttons",
                    "x": 0.1,
                    "xanchor": "right",
                    "y": 0,
                    "yanchor": "top",
                }
            ],
        )
        fig.show()
        if write_html_name:
            fig.write_html(write_html_name)

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

    def plot_interactive_CPU_freq_time_raw(
        self,
        threads: Optional[list[int]] = None,
    ) -> List[go.Scatter]:
        """
        Plot raw scatters of CPU frequency metrics over time.

        You can use these scatters to build your own fig.

        Args:
            threads (Optional[list[int]], optional): CPU threads. Defaults to None, means choose 'all' CPU thread.

        Returns:
            List[go.Scatter]: list of raw scatter plots.
        """
        df = self.get_CPU_frequency()
        df = (
            df[df["CPU"].isin([str(t) for t in threads])]
            if threads
            else df.query("CPU=='all'")
        )
        df = trans_time_to_seconds(df)

        scatters = []
        if threads:
            for t in threads:
                cpu_data = df[df["CPU"] == str(t)]
                seed = random.randint(1, 256)
                r, g, b = generate_unique_rgb_color([t, seed])
                scatters.append(
                    go.Scatter(
                        x=cpu_data["timestamp"],
                        y=cpu_data["MHz"],
                        mode="lines+markers",
                        name=f"CPU{t} freq",
                        # different colors
                        line=dict(color=f"rgb({r}, {g}, {b})"),
                    )
                )
        else:
            seed = random.randint(1, 256)
            r, g, b = generate_unique_rgb_color([seed])
            scatters.append(
                go.Scatter(
                    x=df["timestamp"],
                    y=df["MHz"],
                    mode="lines+markers",
                    name="CPU All freq",
                    # different colors
                    line=dict(color=f"rgb({r}, {g}, {b})"),
                )
            )
        return scatters

    def plot_interactive_CPU_freq_time(
        self,
        threads: Optional[List[int]] = None,
        write_html_name: Optional[str] = None,
    ):
        """
        Generates an interactive plot of the CPU frequency trend over time.

        This method calls another method to obtain raw data for the CPU frequency trend and then uses Plotly to generate
        an interactive line chart. If a file name is specified, the chart is saved as an HTML file.

        Parameters:
        - threads: Optional[List[int]] - A list of thread numbers to specify which threads' frequency trends to plot. If None, it may default to all threads or follow the behavior defined in the called method.
        - write_html_name: Optional[str] - The name of the file to save the generated HTML chart. If None, the chart is not saved.

        Returns:
        - None
        """
        scatters = self.plot_interactive_CPU_freq_time_raw(threads)
        fig = go.Figure()
        for s in scatters:
            fig.add_trace(s)
        fig.update_layout(
            title="CPU Freq Trend",
            xaxis_title="Timestamp",
            yaxis_title="MHz",
            hovermode="closest",
            updatemenus=[
                {
                    "direction": "left",
                    "pad": {"r": 10, "t": 87},
                    "showactive": False,
                    "type": "buttons",
                    "x": 0.1,
                    "xanchor": "right",
                    "y": 0,
                    "yanchor": "top",
                }
            ],
        )
        fig.show()
        if write_html_name:
            fig.write_html(write_html_name)

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
        return self.filter_dataframe(self.sar_data[idx], data_type).astype(astype_t)

    def plot_interactive_network_stat_time_raw(
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
    ) -> List[go.Scatter]:
        """
        Plots interactive network statistics over time.

        This function generates an interactive time series plot for the specified network devices and metrics.
        It can plot either transmission metrics or error metrics based on the `on_failures` flag.

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
        df = df[df["IFACE"].isin(devs)]
        df = trans_time_to_seconds(df)

        scatters = []
        for t in devs:
            dev_data = df[df["IFACE"] == t]
            for i, y in enumerate(metrics):
                seed = random.randint(1, 256)
                r, g, b = generate_unique_rgb_color([t, i, seed])
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
        return scatters

    def plot_interactive_network_stat_time(
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
        on_failures: bool = False,
        write_html_name: Optional[str] = None,
    ):
        """
        Plots interactive network statistics over time and optionally writes the plot to an HTML file.

        This function generates an interactive time series plot for the specified network devices and metrics.
        It can plot either transmission metrics or error metrics based on the `on_failures` flag. The plot can be
        displayed and optionally saved as an HTML file.

        Args:
            devs (list[str]): A list of network device names to include in the plot.
            trans_metrics (List[Literal], optional): A list of transmission metrics to plot. Defaults to `["%ifutil"]`.
            err_metrics (List[Literal], optional): A list of error metrics to plot. Defaults to `["rxerr/s"]`.
            on_failures (bool, optional): If True, plots error metrics; otherwise, plots transmission metrics. Defaults to False.
            write_html_name (Optional[str], optional): The filename to save the plot as an HTML file. If None, the plot is not saved. Defaults to None.
        """
        scatters = self.plot_interactive_network_stat_time_raw(
            devs=devs,
            trans_metrics=trans_metrics,
            err_metrics=err_metrics,
            on_failures=on_failures,
        )
        fig = go.Figure()
        for s in scatters:
            fig.add_trace(s)
        fig.update_layout(
            title="Net Err Trend" if on_failures else "Net Stat Trend",
            xaxis_title="Timestamp",
            yaxis_title="Net Stat",
            hovermode="closest",
            updatemenus=[
                {
                    "direction": "left",
                    "pad": {"r": 10, "t": 87},
                    "showactive": False,
                    "type": "buttons",
                    "x": 0.1,
                    "xanchor": "right",
                    "y": 0,
                    "yanchor": "top",
                }
            ],
        )
        fig.show()
        if write_html_name:
            fig.write_html(write_html_name)

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

    def plot_interactive_mem_usage_time_raw(
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
    ) -> List[go.Scatter]:
        """
        Generates interactive memory usage time series plots.

        This function creates a list of Plotly Scatter objects representing the time series data for the specified memory metrics.
        Each metric is plotted with a unique color.

        Args:
            metrics (List[Literal], optional): A list of memory metrics to plot. Defaults to `["%memused"]`.

        Returns:
            List[go.Scatter]: A list of Plotly Scatter objects representing the time series data for each memory metric.
        """
        df = self.get_memory_usage()
        df = trans_time_to_seconds(df)

        scatters = []
        for i, y in enumerate(metrics):
            seed = random.randint(1, 256)
            r, g, b = generate_unique_rgb_color([i, seed])
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
        return scatters

    def plot_interactive_mem_usage_time(
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
        write_html_name: Optional[str] = None,
    ):
        """
        Plots interactive memory usage time series and optionally writes the plot to an HTML file.

        This function generates an interactive time series plot for the specified memory metrics.
        The plot can be displayed and optionally saved as an HTML file.

        Args:
            metrics (List[Literal], optional): A list of memory metrics to plot. Defaults to `["%memused"]`.
            write_html_name (Optional[str], optional): The filename to save the plot as an HTML file. If None, the plot is not saved. Defaults to None.
        """
        scatters = self.plot_interactive_mem_usage_time_raw(metrics)
        fig = go.Figure()
        for s in scatters:
            fig.add_trace(s)
        fig.update_layout(
            title="Memory Metrics Trend",
            xaxis_title="Timestamp",
            yaxis_title="Memory Usage",
            hovermode="closest",
            updatemenus=[
                {
                    "direction": "left",
                    "pad": {"r": 10, "t": 87},
                    "showactive": False,
                    "type": "buttons",
                    "x": 0.1,
                    "xanchor": "right",
                    "y": 0,
                    "yanchor": "top",
                }
            ],
        )
        fig.show()
        if write_html_name:
            fig.write_html(write_html_name)

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

    def plot_interactive_disk_usage_time_raw(
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
    ) -> List[go.Scatter]:
        """
        Generates interactive disk usage time series plots.

        This function creates a list of Plotly Scatter objects representing the time series data for the specified disk devices and metrics.
        Each metric for each device is plotted with a unique color.

        Args:
            devs (list[str]): A list of disk device names to include in the plot.
            metrics (List[Literal], optional): A list of disk usage metrics to plot. Defaults to `["%util"]`.

        Returns:
            List[go.Scatter]: A list of Plotly Scatter objects representing the time series data for each disk device and metric.
        """
        if len(devs) < 1:
            return []
        df = self.get_disk_usage()
        df = df[df["DEV"].isin(devs)]
        df = trans_time_to_seconds(df)

        scatters = []
        for t in devs:
            cpu_data = df[df["DEV"] == t]
            for i, y in enumerate(metrics):
                seed = random.randint(1, 256)
                r, g, b = generate_unique_rgb_color([t, i, seed])
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
        return scatters

    def plot_interactive_disk_usage_time(
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
        write_html_name: Optional[str] = None,
    ):
        """
        Plots interactive disk usage time series and optionally writes the plot to an HTML file.

        This function generates an interactive time series plot for the specified disk devices and metrics.
        The plot can be displayed and optionally saved as an HTML file.

        Args:
            devs (list[str]): A list of disk device names to include in the plot.
            metrics (List[Literal], optional): A list of disk usage metrics to plot. Defaults to `["%util"]`.
            write_html_name (Optional[str], optional): The filename to save the plot as an HTML file. If None, the plot is not saved. Defaults to None.
        """
        scatters = self.plot_interactive_disk_usage_time_raw(devs=devs, metrics=metrics)
        fig = go.Figure()
        for s in scatters:
            fig.add_trace(s)
        fig.update_layout(
            title="Disk Usage Trend",
            xaxis_title="Timestamp",
            yaxis_title="Disk Usage",
            hovermode="closest",
            updatemenus=[
                {
                    "direction": "left",
                    "pad": {"r": 10, "t": 87},
                    "showactive": False,
                    "type": "buttons",
                    "x": 0.1,
                    "xanchor": "right",
                    "y": 0,
                    "yanchor": "top",
                }
            ],
        )
        fig.show()
        if write_html_name:
            fig.write_html(write_html_name)

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
        write_html_name: Optional[str] = None,
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
            net_trans_metrics (List[Literal], optional): A list of network transmission metrics to plot. Defaults to `["%ifutil"]`.
            net_err_metrics (List[Literal], optional): A list of network error metrics to plot. Defaults to `["rxerr/s"]`.
            mem_metrics (List[Literal], optional): A list of memory metrics to plot. Defaults to `["%memused"]`.
            disk_metrics (List[Literal], optional): A list of disk usage metrics to plot. Defaults to `["%util"]`.
            write_html_name (Optional[str], optional): The filename to save the plot as an HTML file. If None, the plot is not saved. Defaults to None.
            height (int, optional): The height of the plot in pixels. Defaults to 1000.
            shared_xaxes (bool, optional): Whether to share the x-axis across subplots. Defaults to True.
            vertical_spacing (float, optional): The vertical spacing between subplots. Defaults to 0.1.
        """
        cpu_util_scatters = self.plot_interactive_CPU_metrics_time_raw(
            threads=cpu_threads, metrics=cpu_metrics
        )
        cpu_freq_scatters = self.plot_interactive_CPU_freq_time_raw(threads=cpu_threads)
        net_trans_scatters = self.plot_interactive_network_stat_time_raw(
            on_failures=False, devs=net_devs, trans_metrics=net_trans_metrics
        )
        net_err_scatters = self.plot_interactive_network_stat_time_raw(
            on_failures=True, devs=net_devs, err_metrics=net_err_metrics
        )
        mem_scatters = self.plot_interactive_mem_usage_time_raw(metrics=mem_metrics)
        disk_scatters = self.plot_interactive_disk_usage_time_raw(
            devs=disk_devs, metrics=disk_metrics
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
        fig.show()
        if write_html_name:
            fig.write_html(write_html_name)


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

    Args:
        df (pandas.DataFrame): The DataFrame containing the timestamp column.

    Returns:
        pandas.DataFrame: The DataFrame with the timestamp column transformed to seconds.
    """
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%H:%M:%S")
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
