import pandas as pd


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
    return pd.read_csv(
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
    )
