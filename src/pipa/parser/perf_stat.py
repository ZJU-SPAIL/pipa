import pandas as pd
from pipa.common.logger import logger
from pipa.common.utils import generate_unique_rgb_color
from pipa.parser import make_single_plot
from typing import List, Optional, TextIO, Union
import seaborn as sns
import plotly.graph_objects as go


class PerfStatParser:
    @staticmethod
    def parse_perf_stat_file(
        stat_output_path_or_buffer: Union[str, TextIO],
    ) -> pd.DataFrame:
        """
        Parses a perf stat CSV file with a robust "pivot and melt" approach.

        This function is designed to handle various output formats from different `perf`
        versions, including those with varying column counts for different event types
        (e.g., 'instructions' having more columns than 'cycles'). It correctly
        distinguishes between per-CPU and aggregation modes.

        The core logic first transforms the raw long-format data into a tidy,
        wide-format DataFrame. It then melts this wide DataFrame back to the
        long format required by downstream processors like `PerfStatDataProcessor`,
        ensuring full backward compatibility while maintaining high parsing robustness.

        Args:
            stat_output_path_or_buffer (Union[str, TextIO]): The path to the file,
                or a file-like object (e.g., from io.StringIO).

        Returns:
            pandas.DataFrame: A long-format DataFrame containing the parsed data.
            The DataFrame is guaranteed to have the following core columns, which are
            essential for downstream analysis:
            - timestamp (float64): Timestamp of the measurement in seconds.
            - cpu_id (int): The CPU core identifier (-1 for aggregation mode).
            - value (Int64): The raw counter value for the event.
            - metric_type (str): The name of the performance event (e.g., 'cycles:D').

        The expected fields in the raw `perf stat` output are generally in this order,
        though this parser is robust against variations:
        -   optional timestamp in fractions of a second
        -   optional CPU, core, or socket identifier
        -   counter value
        -   optional unit of the counter value
        -   event name
        -   ... and other optional metric fields
        """
        try:
            df = pd.read_csv(
                stat_output_path_or_buffer, header=None, comment="#", engine="python"
            )
        except Exception as e:
            logger.error(f"Failed to read CSV file {stat_output_path_or_buffer}: {e}")
            return pd.DataFrame()

        if df.shape[1] < 3:  # 聚合模式至少需要3列
            logger.warning("CSV file seems malformed with less than 3 columns.")
            return pd.DataFrame()

        second_column_sample = str(df.iloc[0, 1])
        is_per_cpu_mode = second_column_sample.startswith("CPU")

        if is_per_cpu_mode:
            event_col_index = -1
            # 如果数据行数为0，则无法通过iloc访问，因此需要先检查，
            # 但是在for循环内部每次检查一次df是否为空则是无意义的，
            # 因为如果 df 是空的，for 循环根本就不会执行，
            # 因此>0的检查可以规避这个错误
            if df.shape[0] > 0:
                for i in range(3, df.shape[1]):
                    if ":" in str(df.iloc[0, i]):
                        event_col_index = i
                        break

            if event_col_index == -1:
                logger.error(
                    "Could not find event name column (e.g., 'cycles:D') in CSV."
                )
                return pd.DataFrame()

            core_df = df.iloc[:, [0, 1, 2, event_col_index]].copy()
            core_df.columns = ["timestamp", "cpu_id", "value", "metric_type"]
            core_df["cpu_id"] = core_df["cpu_id"].str.removeprefix("CPU").astype(int)
        else:
            core_df = df.iloc[:, [0, 1, 3]].copy()
            core_df.columns = ["timestamp", "value", "metric_type"]
            core_df["cpu_id"] = -1

        core_df["value"] = pd.to_numeric(core_df["value"], errors="coerce")
        core_df.dropna(subset=["value"], inplace=True)
        if not core_df.empty:
            core_df["value"] = core_df["value"].astype("Int64")

        wide_df = core_df.pivot_table(
            index=["timestamp", "cpu_id"],
            columns="metric_type",
            values="value",
            aggfunc="first",
        ).reset_index()
        wide_df.columns.name = None

        long_df = wide_df.melt(
            id_vars=["timestamp", "cpu_id"], var_name="metric_type", value_name="value"
        )

        long_df.dropna(subset=["value"], inplace=True)
        long_df["value"] = long_df["value"].astype("Int64")

        final_long_df = long_df[["timestamp", "cpu_id", "value", "metric_type"]].copy()
        final_long_df = final_long_df.astype(
            {"timestamp": "float64", "cpu_id": "int", "metric_type": "str"}
        )

        logger.info("Perf stat file parsed successfully with robust method.")
        return final_long_df


class PerfStatDataProcessor:
    def __init__(self, data):
        self.data = data.copy()
        self._df_wider = None
        self.data["cpu_id"] = self.data["cpu_id"].astype(int)
        self.data["value"] = pd.to_numeric(self.data["value"], errors="coerce")
        self.data.dropna(subset=["value"], inplace=True)
        if not self.data.empty:
            self.data["value"] = self.data["value"].astype("Int64")

    def get_CPI(self):
        """
        Returns the CPI (Cycles Per Instruction) data.

        Returns:
            pd.DataFrame: Dataframe containing the CPI data.
        """
        return (
            self.data[self.data["metric_type"].str.startswith("cycles")]
            .merge(
                self.data[self.data["metric_type"].str.startswith("instructions")],
                on=["timestamp", "cpu_id"],
                suffixes=("_cycles", "_instructions"),
            )
            .assign(CPI=lambda x: x["value_cycles"] / x["value_instructions"])
            .drop(columns=["metric_type_cycles", "metric_type_instructions"])
        )

    def get_CPI_time(self, threads: list | None = None):
        """
        Returns the CPI (Cycles Per Instruction) over time for the specified threads.

        Args:
            threads (list, optional): A list of thread IDs. If None, returns the average CPI over time for all threads.

        Returns:
            pandas.DataFrame: A DataFrame containing the timestamp and CPI values over time.

        """
        if threads is None:
            return self.get_CPI()[["timestamp", "CPI"]].groupby("timestamp").mean()
        df = self.get_CPI()
        return df[df["cpu_id"].isin([int(t) for t in threads])]

    def get_CPI_overall(self, data_type="thread"):
        """
        Calculate the overall CPI (Cycles Per Instruction) based on the given data type.

        Parameters:
        - data_type (str): The type of data to calculate CPI for. Can be "thread" or "system".

        Returns:
        - If data_type is "thread", returns a DataFrame with CPI values per thread.
        - If data_type is "system", returns the overall CPI value for the system.

        Raises:
        - ValueError: If an invalid data type is provided.
        """

        df = self.get_CPI()
        match data_type:
            case "thread":
                data_per_thread = (
                    df[["cpu_id", "value_cycles", "value_instructions"]]
                    .groupby("cpu_id")
                    .sum()
                )
                data_per_thread["CPI"] = (
                    data_per_thread["value_cycles"]
                    / data_per_thread["value_instructions"]
                )
                return data_per_thread
            case "system":
                total_instructions = df["value_instructions"].sum()
                total_cycles = df["value_cycles"].sum()
                return total_cycles / total_instructions
            case _:
                raise ValueError("Invalid data type")

    def get_CPI_by_thread(self, threads: list):
        """
        Returns the weighted CPI (Cycles Per Instruction) for the specified threads.

        Args:
            threads (list): A list of thread IDs.

        Returns:
            float: The weighted CPI value for the specified threads.
        """
        df = self.get_CPI_overall("thread")
        cycles_sum = df["value_cycles"].sum()
        instructions_sum = df["value_instructions"].sum()
        return cycles_sum / instructions_sum

    def get_CPI_average_by_thread(self, threads: list):
        """
        Returns the average CPI (Cycles Per Instruction) for the specified threads.

        Args:
            threads (list): A list of thread IDs.

        Returns:
            float: The average CPI value for the specified threads.
        """
        return self.get_CPI_overall("thread").loc[threads]["CPI"].mean()

    def get_events_overall(self, events: str, data_type="thread"):
        """
        Calculate the overall events based on the given data type.

        Parameters:
        - events (str): The type of events to calculate. Can be "cache-references", "cache-misses", "branch-misses", etc.
        - data_type (str): The type of data to calculate events for. Can be "thread" or "system".

        Returns:
        - If data_type is "thread", returns a DataFrame with events values per thread.
        - If data_type is "system", returns the overall events value for the system.

        Raises:
        - ValueError: If an invalid data type is provided.
        """
        df = self.data[self.data["metric_type"].str.startswith(events)]
        match data_type:
            case "thread":
                return df[["cpu_id", "value"]].groupby("cpu_id").sum()
            case "system":
                return df["value"].sum()
            case _:
                raise ValueError("Invalid data type")

    def get_cycles_overall(self, data_type="thread"):
        """
        Calculate the overall cycles based on the given data type.

        Parameters:
        - data_type (str): The type of data to calculate cycles for. Can be "thread" or "system".

        Returns:
        - If data_type is "thread", returns a DataFrame with cycles values per thread.
        - If data_type is "system", returns the overall cycles value for the system.

        Raises:
        - ValueError: If an invalid data type is provided.
        """
        return self.get_events_overall("cycles", data_type)

    def get_instructions_overall(self, data_type="thread"):
        """
        Calculate the overall instructions based on the given data type.

        Parameters:
        - data_type (str): The type of data to calculate instructions for. Can be "thread" or "system".

        Returns:
        - If data_type is "thread", returns a DataFrame with instructions values per thread.
        - If data_type is "system", returns the overall instructions value for the system.

        Raises:
        - ValueError: If an invalid data type is provided.
        """
        return self.get_events_overall("instructions", data_type)

    def get_cycles_by_thread(self, threads=None):
        """
        Returns the total cycles per thread.

        Args:
            threads (list): A list of thread IDs.

        Returns:
            pd.DataFrame: A DataFrame containing the total cycles per thread.
        """
        if threads is None:
            return self.get_cycles_overall("thread")["value"].sum()
        return self.get_cycles_overall("thread").loc[threads]["value"].sum()

    def get_instructions_by_thread(self, threads=None):
        """
        Returns the total instructions per thread.

        Args:
            threads (list): A list of thread IDs.

        Returns:
            int: The total instructions in all threads used.
        """
        if threads is None:
            return self.get_instructions_overall("system")
        return self.get_instructions_overall("thread").loc[threads]["value"].sum()

    def get_pathlength(self, num_transcations: int, threads: list):
        """
        Returns the pathlength for the given number of transcations and threads.

        Args:
            num_transcations (int): The number of transcations.
            threads (list): A list of thread IDs.

        Returns:
            float: The pathlength value.
        """
        insns = self.get_instructions_by_thread(threads)
        path_length = insns / num_transcations
        return path_length

    def get_cycles_per_second(self, seconds: int = 120, threads=None):
        """
        Returns the total cycles per second.

        Args:
            seconds (int): The number of seconds. Default is 120.
            threads (list): A list of thread IDs. Default is None.

        Returns:
            int: The total cycles per second.
        """
        return self.get_cycles_by_thread(threads) / seconds

    def get_instructions_per_second(self, seconds: int = 120, threads=None):
        """
        Returns the total instructions per second.

        Args:
            seconds (int): The number of seconds. Default is 120.
            threads (list): A list of thread IDs. Default is None.

        Returns:
            int: The total instructions per second.
        """
        return self.get_instructions_by_thread(threads) / seconds

    def get_time_range(self):
        """
        Returns the time range of the data.

        Returns:
            tuple: A tuple containing the minimum and maximum timestamps.
        """
        return self.data["timestamp"].min(), self.data["timestamp"].max()

    def get_time_delta(self):
        """
        Returns the time delta of the data.

        Returns:
            float: The time delta between timestamps.
        """
        return self.data["timestamp"].diff().mean()

    def get_time_total(self):
        """
        Returns the total time of the data.

        Returns:
            float: The total time of the data.
        """
        return self.data["timestamp"].max() - self.data["timestamp"].min()  # in seconds

    def is_multiplexing(self):
        """
        Check if the data contains multiplexing.

        Returns:
            bool: True if the data contains multiplexing, False otherwise.
        """
        return not self.data["run_percentage"].astype(float).eq(100.0).all()

    def get_wider_data(self):
        """
        Get the wider data with columns for each metric type.
        Tidy the data by pivoting the metric_type column.

        Returns:
            pd.DataFrame: The wider data.
        """
        if self._df_wider is not None:
            return self._df_wider
        df = self.data[["timestamp", "cpu_id", "value", "metric_type"]]
        df_wider = df.pivot_table(
            index=["timestamp", "cpu_id"],
            columns="metric_type",
            values="value",
            aggfunc="first",
        ).reset_index()
        df_wider.columns = [f"{col}" for col in df_wider.columns]
        self._df_wider = df_wider
        return df_wider

    def get_tidy_data(self, thread_list: list = None):
        """
        Get the tidied data with columns for each metric type.
        Tidy the data by pivoting the metric_type column.

        ```
        Args:
            thread_list (list, optional): A list of hardware thread names to include in the tidy data.
            If None, all threads are included. Default is None.

        Returns:
            pd.DataFrame: The tidied data.
        ```
        """
        df = self.get_wider_data()
        if thread_list:
            thread_list = [int(cpu) for cpu in thread_list]
            df = df[df["cpu_id"].isin(thread_list)]
            if len(thread_list) == 1:
                return df
        df_t = df.pivot_table(index=["timestamp"], columns="cpu_id").reset_index()
        df_t.columns = [f"{col[0]}_{col[1]}" for col in df_t.columns]
        df_t.rename(columns={"timestamp_": "timestamp"}, inplace=True)
        return df_t

    def get_available_events(self) -> List[str]:
        """Get all available events in the data.

        Returns:
            List[str]: list of avaiable events.
        """
        df = self.get_wider_data()
        col = df.columns.copy()
        col = col.drop(["timestamp", "cpu_id"])
        return col.to_list()


class PerfStatPlotter:
    def __init__(self, data_processor: PerfStatDataProcessor):
        self.data_processor = data_processor

    def plot_CPI_time_by_thread(self, threads: list):
        """
        Plots CPI over time for the specified threads.

        Args:
            threads (list): A list of thread IDs.

        Returns:
            None
        """
        sns.set_theme(style="darkgrid", rc={"figure.figsize": (15, 8)})
        if len(threads) > 1:
            p = sns.lineplot(
                data=self.data_processor.get_CPI_time(threads),
                x="timestamp",
                hue="cpu_id",
                y="CPI",
            )
        else:
            p = sns.lineplot(
                data=self.data_processor.get_CPI_time(threads), x="timestamp", y="CPI"
            )
        p.set_title("CPI over Time, Thread " + ",".join([str(t) for t in threads]))
        p.set_xlabel("Time(s)")
        p.set_ylabel("CPI")
        return p

    def plot_CPI_time_system(self):
        """
        Plots CPI (Cycles Per Instruction) over time for the system.

        This method generates a line plot showing the CPI values over time for the system.
        It uses the data returned by the `get_CPI_time` method and saves the plot as an image.

        Returns:
            None
        """
        sns.set_theme(style="darkgrid", rc={"figure.figsize": (15, 8)})
        p = sns.lineplot(
            data=self.data_processor.get_CPI_time(), x="timestamp", y="CPI"
        )
        p.set_title("CPI over Time, System")
        p.set_xlabel("Time(s)")
        p.set_ylabel("CPI")
        return p

    def plot_interactive_event(
        self,
        events: Optional[List[str]] = None,
        threads: Optional[List[int]] = None,
        aggregation: bool = False,
        raw_data: bool = False,
        show: bool = True,
        write_to_html: Optional[str] = None,
    ) -> List[go.Scatter]:
        df = self.data_processor.get_wider_data()
        scatters = []
        if threads:
            df = df[df["cpu_id"].isin(threads)]
        if aggregation:
            df = df.groupby(["timestamp"]).mean(numeric_only=True).reset_index()
            df["cpu_id"] = "all"
        # prevent duplicated events
        if events:
            events = list(set(events))
        else:
            events = df.columns.copy()
            events = events.drop(["timestamp", "cpu_id"])
        avail_threads = df["cpu_id"].unique().tolist()
        for t in avail_threads:
            data = df[df["cpu_id"] == t]
            for i, y in enumerate(events):
                r, g, b = generate_unique_rgb_color([t, i], generate_seed=True)
                try:
                    scatters.append(
                        go.Scatter(
                            x=data["timestamp"],
                            y=data[y],
                            mode="lines+markers",
                            name=f"CPU {t} {y}",
                            # different colors
                            line=dict(color=f"rgb({r}, {g}, {b})"),
                        )
                    )
                except KeyError as e:
                    logger.warning(f"Not found event: {y} in the stat data: {e}")
        if raw_data:
            return scatters
        else:
            return make_single_plot(
                scatters=scatters,
                title="Stat events trend",
                xaxis_title="Timestamp",
                yaxis_title="Value",
                show=show,
                write_to_html=write_to_html,
            )


class PerfStatData:
    def __init__(self, perf_stat_csv_path: Union[str, TextIO]):
        self.data = PerfStatParser.parse_perf_stat_file(perf_stat_csv_path)
        self.data_processor = PerfStatDataProcessor(self.data)
        self.plotter = PerfStatPlotter(self.data_processor)

    def __getattr__(self, name):
        if hasattr(self.data_processor, name):
            return getattr(self.data_processor, name)
        if hasattr(self.plotter, name):
            return getattr(self.plotter, name)
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )
