from pipa.parser.sar import SarData
from pipa.parser.perf_stat import PerfStatData
from pipa.parser.perf_script_call import PerfScriptData


class PIPAShuData:
    """
    A class representing PipaShu data.

    Attributes:
        sar_data (SarData): The SAR data.
        perf_stat_data (PerfStatData): The performance statistics data.
        perf_record_data (Optional): The performance record data.

    Methods:
        __init__: Initialize a PipaShuData object with data from text files.
        init_without_data: Initialize a PipaShuData object without data.
        get_metrics: Get the performance statistics metrics.
    """

    def __init__(self, perf_stat_path, sar_path, perf_record_path=None):
        """
        Initialize a PipaShuData object with data from text files.

        Args:
            perf_stat_path (str): The path to the performance statistics text file.
            sar_path (str): The path to the SAR data text file.
            perf_record_data: The performance record data.

        Returns:
            None
        """
        self.sar_data = SarData.init_with_sar_txt(sar_path)
        self.perf_stat_data = PerfStatData(perf_stat_path)
        self.perf_record_data = (
            PerfScriptData.from_file(perf_record_path) if perf_record_path else None
        )

    @classmethod
    def init_without_data(cls):
        """
        Initialize a PipaShuData object without data.

        Returns:
            None
        """
        return cls(None, None, None)

    def get_metrics(
        self,
        num_transactions: int,
        threads: list,
        run_time: int = None,
        dev: str | None = None,
        freq_MHz: int = None,
    ):
        """
        Get the performance statistics metrics.

        Args:
            num_transactions (int): The number of transactions.
            threads (list): The list of threads.
            run_time (int): The run time.
            dev (str): The device name.
            freq_MHz (int): The CPU frequency in MHz.

        Returns:
            dict: The performance statistics metrics.
        """
        run_time = self.perf_stat_data.get_time_total() if not run_time else run_time

        cycles = self.perf_stat_data.get_cycles_by_thread(threads)
        instructions = self.perf_stat_data.get_instructions_by_thread(threads)
        cycles_per_second = self.perf_stat_data.get_cycles_per_second(run_time, threads)
        instructions_per_second = self.perf_stat_data.get_instructions_per_second(
            run_time, threads
        )
        path_length = self.perf_stat_data.get_pathlength(num_transactions, threads)
        CPI = self.perf_stat_data.get_CPI_by_thread(threads)
        cycles_per_requests = cycles / num_transactions

        perf_stat_metrics = {
            "transactions": num_transactions,
            "throughput": num_transactions / run_time,
            "used_threads": threads,
            "run_time": run_time,
            "cycles": cycles,
            "instructions": instructions,
            "cycles_per_second": cycles_per_second,
            "instructions_per_second": instructions_per_second,
            "CPI": CPI,
            "cycles_per_requests": cycles_per_requests,
            "path_length": path_length,
        }

        sar_cpu = self.sar_data.get_CPU_util_avg_summary(threads)
        sar_freq = self.sar_data.get_cpu_freq_avg(threads)

        if sar_freq["cpu_frequency_mhz"] == 0 and freq_MHz:
            sar_freq["cpu_frequency_mhz"] = freq_MHz

        sar_mem = self.sar_data.get_memory_usage_avg()
        sar_disk = self.sar_data.get_disk_usage_avg(dev)

        if dev is None:
            # Get the disk with the highest utilization if no device is specified
            sar_disk = max(sar_disk, key=lambda x: x["%disk_util"])

        return {**perf_stat_metrics, **sar_cpu, **sar_freq, **sar_mem, **sar_disk}
