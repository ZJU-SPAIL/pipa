from .upload import load, build
import yaml


def format(d: dict):
    """
    Formats the values in the given dictionary as floats.

    Args:
        d (dict): The dictionary containing the values to be formatted.

    Returns:
        dict: The dictionary with the values formatted as floats.
            - CPI (float): The cycles per instruction.
            - run_time (float): The run time of the workload.
            - cycles (float): The number of cycles.
            - instructions (float): The number of instructions.
            - path_length (float): The path length.
            - instructions_per_second (float): The instructions per second.
            - cycles_per_second (float): The cycles per second.
            - cycles_per_requests (float): The cycles per request.
            - throughput (float): The throughput.
    """
    d["CPI"] = float(d["CPI"])
    d["run_time"] = float(d["run_time"])
    d["cycles"] = float(d["cycles"])
    d["instructions"] = float(d["instructions"])
    d["path_length"] = float(d["path_length"])
    d["instructions_per_second"] = float(d["instructions_per_second"])
    d["cycles_per_second"] = float(d["cycles_per_second"])
    d["cycles_per_requests"] = float(d["cycles_per_requests"])
    d["throughput"] = float(d["throughput"])
    return d


def dump(output_path: str, config_path: str = None, verbose: bool = False):
    """
    Dump the data to a YAML file.

    Args:
        output_path (str): The path to the output file.
        config_path (str, optional): The path to the configuration file. Defaults to None.
        verbose (bool, optional): Whether to display verbose output. Defaults to False.

    Returns:
        dict: The dumped data.
    """
    data = load(config_path, verbose)
    with open(output_path, "w") as file:
        yaml.dump(build(data), file)
    return data


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Dump PIPASHU overview data to a file")
    parser.add_argument("-o", "--output_path", help="Path to the output file")
    parser.add_argument(
        "-c", "--config", help="Path to the configuration file", default=None
    )
    parser.add_argument("-v", "--verbose", help="Verbose mode", action="store_true")
    args = parser.parse_args()
    dump(args.output_path, args.config, args.verbose)
