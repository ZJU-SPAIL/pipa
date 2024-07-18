from pipa.service.gengerate.common import load_yaml_config
from pipa.service.gengerate.run_by_pipa import generate as generate_pipa
from pipa.service.gengerate.run_by_user import generate as generate_user
from pipa.common.hardware.cpu import get_cpu_cores

import questionary


def build_command(use_taskset: bool, core_range, command):
    """
    Builds a command with optional taskset and core range.

    Args:
        use_taskset (bool): Whether to use taskset for CPU affinity.
        core_range (str): The range of CPU cores to use.
        command (str): The command to be executed.

    Returns:
        str: The built command.

    Raises:
        ValueError: If the core range is not a valid range or contains non-digit characters.

    """
    if use_taskset:
        CORES_ALL = get_cpu_cores()
        if core_range.isdigit():
            core_list = core_range.strip()
        elif core_range.split("-").__len__() != 2:
            raise ValueError("Please input cores as a valid range, split by '-'.")
        else:
            left, right = core_range.split("-")

            left, right = left.strip(), right.strip()
            if not left.isdigit() or not right.isdigit():
                raise ValueError("Please input cores as a valid range, non-digit char detected.")
            left, right = int(left), int(right)
            if left < CORES_ALL[0] or right > CORES_ALL[-1] or left > right:
                raise ValueError("Please input cores as a valid range.")
            core_list = ",".join([str(i) for i in list(range(left, right + 1))])

        command = f"/usr/bin/taskset -c {core_list} {command}"
    return command


def quest():
    """
    Asks the user for the location of the configuration file of PIPA-SHU.

    Returns:
        str: The path to the configuration file.
    """
    config_yaml = questionary.text(
        "Where is the configuration file of PIPA-SHU?\n", "./config-pipa-shu.yaml"
    ).ask()
    return config_yaml


def build(path: str):
    """
    Builds the configuration based on the provided path.

    Args:
        path (str): The path to the configuration file.

    Returns:
        None
    """
    config = load_yaml_config(path)
    config["events_stat"] = ",".join(config["events_stat"])
    build_command(config["use_taskset"], config["core_range"], config["command"])
    if config["run_by_perf"]:
        generate_pipa(config)
    else:
        generate_user(config)


def main(config_path: str = None):
    """
    Main function for parsing Pipashu configuration.

    Args:
        config_path (str, optional): Path to the configuration file. If not provided, a prompt will be shown to enter the path.

    Returns:
        The result of the `build` function using the provided or prompted configuration path.
    """
    if config_path is None:
        config_path = quest()
    return build(config_path)


if __name__ == "__main__":
    main()
