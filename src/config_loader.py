import subprocess
from pathlib import Path

import yaml


class ConfigError(Exception):
    """Custom exception for configuration errors."""

    pass


def _resolve_shell_commands(node):
    """
    Recursively traverses a config dict/list and executes shell commands.
    递归地遍历配置字典/列表，并执行 shell 命令。
    """
    if isinstance(node, dict):
        for key, value in node.items():
            node[key] = _resolve_shell_commands(value)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            node[i] = _resolve_shell_commands(item)
    elif isinstance(node, str) and node.startswith("$(") and node.endswith(")"):
        command = node[2:-1]
        try:
            result = subprocess.check_output(command, shell=True, text=True).strip()
            try:
                return int(result)
            except ValueError:
                try:
                    return float(result)
                except ValueError:
                    return result
        except subprocess.CalledProcessError:
            raise ConfigError(f"Failed to execute shell command in config: {node}")
    return node


def load_workload_config(workload_name: str) -> dict:
    """
    Loads and validates the YAML configuration for a given workload.
    为一个给定的工作负载加载并验证 YAML 配置。

    :param workload_name: The name of the workload (e.g., "mysql").
    :return: A dictionary containing the workload configuration.
    :raises ConfigError: If the config file is not found or invalid.
    """
    config_path = Path(f"config/workloads/{workload_name}.yaml")
    if not config_path.is_file():
        raise ConfigError(f"Workload configuration file not found at: {config_path}")

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Error parsing YAML file {config_path}: {e}")

    resolved_config = _resolve_shell_commands(config)

    if not isinstance(resolved_config, dict):
        raise ConfigError("Top level of a workload config must be a dictionary.")

    return resolved_config
