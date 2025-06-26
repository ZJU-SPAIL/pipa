import seaborn as sns
from pipa.common.logger import logger
from pipa.common.utils import generate_unique_rgb_color

from .sar_parser import SarParser
from .sar_processor import SarProcessor
from typing import Optional, List, Literal
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pipa.parser import make_single_plot


# Plotter class, responsible for data visualization
class SarPlotter:
    def __init__(self, processor: SarProcessor):
        """
        Initialize the SarPlotter with a SarProcessor instance.

        Args:
            processor (SarProcessor): An instance of SarProcessor containing processed SAR data.
        """
        self.processor = processor

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
        df = self.processor.get_CPU_utilization()
        # minus 'all'
        cpu_counts = df["CPU"].nunique() - 1
        df = SarParser.trans_time_to_seconds(df)
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
        df = self.processor.get_CPU_utilization()
        df = (
            df[df["CPU"].isin([str(t) for t in threads])]
            if threads
            else df.query("CPU=='all'")
        )
        df = SarParser.trans_time_to_seconds(df)

        if threads and len(threads) > 1:
            sns.lineplot(data=df, x="timestamp", y=r"%util", hue="CPU")
        else:
            sns.lineplot(data=df, x="timestamp", y=r"%util")

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
        df = self.processor.get_CPU_frequency()
        # minus 'all'
        cpu_counts = df["CPU"].nunique() - 1
        df = SarParser.trans_time_to_seconds(df)
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
        df = self.processor.get_CPU_frequency()

        sns.set_theme(style="darkgrid", rc={"figure.figsize": (15, 8)})

        df = (
            df[df["CPU"].isin([str(t) for t in threads])]
            if threads
            else df.query("CPU=='all'")
        )
        df = SarParser.trans_time_to_seconds(df)

        if threads and len(threads) > 1:
            sns.lineplot(
                data=df,
                x="timestamp",
                y="MHz",
                hue="CPU",
            )
        else:
            sns.lineplot(data=df, x="timestamp", y="MHz")

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
        df = self.processor.get_network_statistics(on_failures=on_failures)
        df = SarParser.trans_time_to_seconds(df)

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
        df = self.processor.get_memory_usage()
        df = SarParser.trans_time_to_seconds(df)

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

    def plot_memory_usage(self):
        """
        Plots the memory usage over time.
        """
        df = self.processor.get_memory_usage()
        df = SarParser.trans_time_to_seconds(df)
        sns.lineplot(data=df, x="timestamp", y=r"%memused")

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
        df = self.processor.get_disk_usage()
        df = SarParser.trans_time_to_seconds(df)

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

    def plot_disk_usage(self, dev: str = None, metrics="tps"):
        """
        Plots the disk tps over time.
        """
        df = self.processor.get_disk_usage()
        df = SarParser.trans_time_to_seconds(df)
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
    ) -> go.Figure:
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
