import logging
import re
import subprocess

import yaml

from .utils import get_project_root

log = logging.getLogger(__name__)


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
    project_root = get_project_root()
    config_path = project_root / f"config/workloads/{workload_name}.yaml"
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


def _sanitize_model_name(model_name: str) -> str:
    """将 CPU Model Name 清理为安全的文件名。"""
    if not model_name:
        return ""
    sanitized = model_name.lower()
    sanitized = re.sub(r"\(r\)|\(tm\)|@.*", "", sanitized)
    sanitized = re.sub(r"\s+", "-", sanitized).strip("-")
    return sanitized


def load_events_config(arch: str, model_name: str) -> dict:
    """
    按“微架构 -> 架构 -> 默认”的顺序，分层加载事件配置文件。
    """
    project_root = get_project_root()
    sanitized_model = _sanitize_model_name(model_name)

    if sanitized_model:
        specific_path = project_root / f"config/events/{sanitized_model}.yaml"
        if specific_path.is_file():
            log.info(f"成功找到并加载微架构特定事件文件: {specific_path.name}")
            try:
                with open(specific_path, "r") as f:
                    return yaml.safe_load(f)
            except yaml.YAMLError as e:
                raise ConfigError(f"解析事件文件 {specific_path.name} 出错: {e}")

    arch_path = project_root / f"config/events/{arch}.yaml"
    if arch_path.is_file():
        log.warning(f"未找到型号 '{sanitized_model}' 的特定事件集，回退到架构通用事件: {arch_path.name}")
        try:
            with open(arch_path, "r") as f:
                return yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError(f"解析事件文件 {arch_path.name} 出错: {e}")

    default_path = project_root / "config/events/x86_64.yaml"
    log.warning(f"架构 '{arch}' 的通用事件集也未找到，回退到最终默认事件: {default_path.name}")
    if not default_path.is_file():
        raise ConfigError("致命错误：连最终的默认事件文件 (x86_64.yaml) 都找不到。")
    try:
        with open(default_path, "r") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"解析事件文件 {default_path.name} 出错: {e}")
