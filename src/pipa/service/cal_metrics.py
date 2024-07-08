from pipa.parser.sar import SarData
from pipa.parser.perf_stat import PerfStatData
from pipa.parser.perf_script import parse_perf_script_file


class PIPAShuData:

    def __init__(self, perf_stat_path, sar_path, perf_record_path=None):
        """
        Initialize a PipaShu object with data from text files.

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
            parse_perf_script_file(perf_record_path) if perf_record_path else None
        )

    @classmethod
    def init_without_data(cls):
        """
        Initialize a PipaShu object without data.

        Returns:
            None
        """
        return cls(None, None, None)

    def get_metrics(
        self, num_transcations: int, threads: list, run_time: int = 120, dev: str = None
    ):
        """
        Get the performance statistics metrics.

        Args:
            num_transcations (int): The number of transactions.
            threads (list): The list of threads.
            run_time (int): The run time.

        Returns:
            dict: The performance statistics metrics.
        """
        cycles = self.perf_stat_data.get_cycles_by_thread(threads)
        instructions = self.perf_stat_data.get_instructions_by_thread(threads)
        cycles_per_second = self.perf_stat_data.get_cycles_per_second(run_time, threads)
        instructions_per_second = self.perf_stat_data.get_instructions_per_second(
            run_time, threads
        )
        path_length = self.perf_stat_data.get_pathlength(num_transcations, threads)
        CPI = self.perf_stat_data.get_CPI_by_thread(threads)
        cycles_per_requests = cycles / num_transcations

        perf_stat_metrics = {
            "use_threads": threads,
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
        sar_mem = self.sar_data.get_memory_usage_avg()
        sar_disk = self.sar_data.get_disk_usage_avg(dev)

        return {**perf_stat_metrics, **sar_cpu, **sar_mem, **sar_disk}
