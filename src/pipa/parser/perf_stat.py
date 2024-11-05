import pandas as pd
from pandarallel import pandarallel
from pipa.common.hardware.cpu import NUM_CORES_PHYSICAL
from pipa.common.logger import logger
import seaborn as sns


class PerfStatData:
    def __init__(self, perf_stat_csv_path: str):
        self.data = self.parse_perf_stat_file(perf_stat_csv_path)
        self._df_wider = None

    def get_CPI(self):
        """
        Returns the CPI (Cycles Per Instruction) data.

        Returns:
            pd.DataFrame: Dataframe containing the CPI data.
        """
        return (
            self.data[self.data["metric_type"] == "cycles"]
            .merge(
                self.data[self.data["metric_type"] == "instructions"],
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
                data=self.get_CPI_time(threads), x="timestamp", hue="cpu_id", y="CPI"
            )
        else:
            p = sns.lineplot(data=self.get_CPI_time(threads), x="timestamp", y="CPI")
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
        p = sns.lineplot(data=self.get_CPI_time(), x="timestamp", y="CPI")
        p.set_title("CPI over Time, System")
        p.set_xlabel("Time(s)")
        p.set_ylabel("CPI")
        return p

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
        df = self.data[self.data["metric_type"] == events]
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
        return all(self.data["run_percentage"].astype(int) == 100)

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

    @staticmethod
    def parse_perf_stat_file(stat_output_path: str):
        """
        Parse the perf stat output file and return a pandas DataFrame.

        Args:
            stat_output_path (str): The path to the perf stat output file.

        Returns:
            pandas.DataFrame: The parsed data as a DataFrame.

        The fields are in this order:
        -   optional usec time stamp in fractions of second (with -I xxx)
        -   optional CPU, core, or socket identifier
        -   optional number of logical CPUs aggregated
        -   counter value
        -   unit of the counter value or empty
        -   event name
        -   run time of counter
        -   percentage of measurement time the counter was running
        -   optional metric value
        -   optional unit of metric
        """
        pandarallel.initialize(min(12, NUM_CORES_PHYSICAL))
        try:
            df = pd.read_csv(
                stat_output_path,
                skiprows=1,
                names=[
                    "timestamp",
                    "cpu_id",
                    "value",
                    "unit",
                    "metric_type",
                    "run_time(ns)",
                    "run_percentage",
                    "opt_value",
                    "opt_unit_metric",
                ],
            ).astype(
                {
                    "timestamp": "float64",
                    "cpu_id": str,
                    "value": "int64",
                    "unit": str,
                    "metric_type": str,
                    "run_time(ns)": "int64",
                    "run_percentage": "float64",
                    "opt_value": "float64",
                    "opt_unit_metric": str,
                }
            )
            df["cpu_id"] = df["cpu_id"].str.removeprefix("CPU").astype(int)
        except pd.errors.IntCastingNaNError as e:
            logger.warning(
                f"Detect perf stat {stat_output_path} not in no aggregation mode(-A), will use use -1 as cpuid for all"
            )
            df = pd.read_csv(
                stat_output_path,
                skiprows=1,
                names=[
                    "timestamp",
                    "value",
                    "unit",
                    "metric_type",
                    "run_time(ns)",
                    "run_percentage",
                    "opt_value",
                    "opt_unit_metric",
                ],
            ).astype(
                {
                    "timestamp": "float64",
                    "value": "int64",
                    "unit": str,
                    "metric_type": str,
                    "run_time(ns)": "int64",
                    "run_percentage": "float64",
                    "opt_value": "float64",
                    "opt_unit_metric": str,
                }
            )
            df["cpu_id"] = -1
        return df
