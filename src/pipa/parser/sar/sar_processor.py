from .sar_index import SarDataIndex
import pandas as pd
from typing import Optional, Dict, List
from pipa.common.logger import logger


# Processor class, responsible for data processing
class SarProcessor:
    def __init__(self, sar_data: List[pd.DataFrame]):
        """
        Initialize the SarProcessor with parsed SAR data.

        Args:
            sar_data (List[pd.DataFrame]): List of DataFrames containing parsed SAR data.
        """
        self.sar_data = sar_data
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

    def filter_dataframe(self, df, data_type: str = "detail") -> pd.DataFrame:
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

    def get_CPU_utilization(self, data_type: str = "detail") -> pd.DataFrame:
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

    def get_CPU_util_avg_by_threads(self, threads: list = None) -> pd.DataFrame:
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

    def get_CPU_util_avg_summary(self, threads: list = None) -> Dict:
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

    def get_CPU_frequency(self, data_type: str = "detail") -> pd.DataFrame:
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

    def get_cpu_freq_avg(self, threads: list = None) -> Dict:
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

    def get_CPU_util_freq(self, data_type: str = "detail") -> pd.DataFrame:
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
    ) -> pd.DataFrame:
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

    def get_network_statistics_avg(self, on_failures: bool = False) -> List[Dict]:
        return (
            self.get_network_statistics(data_type="average", on_failures=on_failures)
            .drop(columns=["timestamp"])
            .to_dict(orient="records")
        )

    def get_memory_usage(self, data_type: str = "detail") -> pd.DataFrame:
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

    def get_memory_usage_avg(self) -> Dict:
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

    def get_disk_usage(
        self, dev: str = None, data_type: str = "detail"
    ) -> pd.DataFrame:
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

    def get_disk_usage_avg(self, dev: str = None) -> List[Dict] | Dict:
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
