from .upload import load
import yaml


def format(d: dict):
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
    data = load(config_path, verbose)
    with open(output_path, "w") as file:
        yaml.dump(data, file)
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
