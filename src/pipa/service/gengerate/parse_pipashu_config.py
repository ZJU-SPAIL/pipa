from pipa.service.gengerate.common import (
    load_yaml_config,
    generate_core_list,
)
from pipa.service.gengerate.run_by_pipa import generate as generate_pipa
from pipa.service.gengerate.run_by_user import generate as generate_user
import questionary


def build_command(use_taskset: bool, core_range: str, command):
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
        core_list = generate_core_list(core_range)
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
