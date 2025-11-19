"""
配置文件加载模块

此模块负责加载和解析YAML格式的配置文件。
提供配置文件的读取、验证和错误处理功能。
"""

import logging
from pathlib import Path

import yaml

log = logging.getLogger(__name__)


class ConfigError(Exception):
    """配置文件相关的自定义异常类。"""


def load_yaml_config(config_path_str: str) -> dict:
    """
    加载并解析指定的YAML配置文件。

    检查文件是否存在，读取文件内容，使用yaml.safe_load解析，
    并验证解析结果是否为字典格式。

    参数:
        config_path_str: 配置文件的路径字符串。

    返回:
        解析后的配置字典。

    异常:
        ConfigError: 如果文件不存在、YAML解析失败或格式不正确。
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
