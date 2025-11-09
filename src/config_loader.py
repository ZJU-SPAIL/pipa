import logging
import re
from pathlib import Path
from typing import Any

import yaml

from .utils import get_project_root

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


def _sanitize_model_name(model_name: str) -> str:
    """Cleans a CPU Model Name into a safe filename."""
    if not model_name:
        return ""
    sanitized = model_name.lower()
    sanitized = re.sub(r"\(r\)|\(tm\)|@.*", "", sanitized)
    sanitized = re.sub(r"\s+", "-", sanitized).strip("-")
    return sanitized


def load_events_config(arch: str, model_name: str) -> dict[str, Any]:
    """
    Loads event configuration files hierarchically: Microarchitecture -> Architecture -> Default.
    按“微架构 -> 架构 -> 默认”的顺序，分层加载事件配置文件。
    """
    project_root = get_project_root()
    sanitized_model = _sanitize_model_name(model_name)

    if sanitized_model:
        specific_path = project_root / f"config/events/{sanitized_model}.yaml"
        if specific_path.is_file():
            log.info(f"Found and loaded microarchitecture-specific event file: {specific_path.name}")
            return load_yaml_config(str(specific_path))

    arch_path = project_root / f"config/events/{arch}.yaml"
    if arch_path.is_file():
        log.warning(f"No specific event set for model '{sanitized_model}', falling back to arch: {arch_path.name}")
        return load_yaml_config(str(arch_path))

    default_path = project_root / "config/events/x86_64.yaml"
    log.warning(f"No arch-specific event set for '{arch}', falling back to final default: {default_path.name}")
    if not default_path.is_file():
        raise ConfigError("Fatal: Could not find the final fallback event file (x86_64.yaml).")
    return load_yaml_config(str(default_path))
