import pandas as pd
from pandarallel import pandarallel
import seaborn as sns


class PerfStatData:
    def __init__(self, perf_stat_csv_path: str):
        self.data = parse_perf_stat_file(perf_stat_csv_path)

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

    def get_CPI_time(self, threads: list = None):
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


def parse_perf_stat_file(stat_output_path: str):
    """
    Parse the perf stat output file and return a pandas DataFrame.

    Args:
        stat_output_path (str): The path to the perf stat output file.

    Returns:
        pandas.DataFrame: The parsed data as a DataFrame.

    The fields are in this order:
    •   optional usec time stamp in fractions of second (with -I xxx)
    •   optional CPU, core, or socket identifier
    •   optional number of logical CPUs aggregated
    •   counter value
    •   unit of the counter value or empty
    •   event name
    •   run time of counter
    •   percentage of measurement time the counter was running
    •   optional metric value
    •   optional unit of metric
    """
    pandarallel.initialize()
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
    return df
