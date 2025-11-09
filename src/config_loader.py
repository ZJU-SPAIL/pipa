import logging
from pathlib import Path

import yaml

log = logging.getLogger(__name__)


class ConfigError(Exception):
    """Custom exception for configuration errors."""


def load_yaml_config(config_path_str: str) -> dict:
    """
    Loads and parses a specified YAML configuration file.
    加载并解析一个指定的 YAML 配置文件。
    """
    config_path = Path(config_path_str)
    log.info(f"Loading configuration file from path: {config_path}")

    if not config_path.is_file():
        raise ConfigError(f"Configuration file not found: {config_path}")

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Error parsing YAML file {config_path}: {e}")

    if not isinstance(config, dict):
        raise ConfigError("The top level of the configuration file must be a dictionary.")

    return config
