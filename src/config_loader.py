import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict

import yaml

from .utils import get_project_root

log = logging.getLogger(__name__)


class ConfigError(Exception):
    """Custom exception for configuration errors."""

    pass


def _resolve_variables_and_commands(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    一个两阶段的解析器：
    1. 解析顶层的 'variables' 块，支持顺序依赖和 shell 命令。
    2. 遍历配置的其余部分，替换 ${variable} 和 $(shell_command)。

    这个设计灵感来自 Dockerfile 的 ARG/ENV 机制，实现了真正的"配置即代码"。
    """
    resolved_vars: Dict[str, Any] = {}
    variable_definitions = config.get("variables", [])

    for var_def in variable_definitions:
        if not isinstance(var_def, dict) or len(var_def) != 1:
            continue
        var_name, raw_value = list(var_def.items())[0]

        if not isinstance(raw_value, str):
            resolved_vars[var_name] = raw_value
            continue

        for res_name, res_value in resolved_vars.items():
            raw_value = raw_value.replace(f"${{{res_name}}}", str(res_value))

        if "$(" in raw_value:
            command = f'echo "{raw_value}"'
            try:
                result = subprocess.check_output(command, shell=True, text=True).strip()
                resolved_vars[var_name] = result
                log.debug(f"变量 '{var_name}' 解析为: {result}")
            except subprocess.CalledProcessError as e:
                raise ConfigError(f"变量 '{var_name}' 的 shell 命令执行失败: {raw_value}\n错误: {e}")
        else:
            resolved_vars[var_name] = raw_value
            log.debug(f"变量 '{var_name}' 设置为: {raw_value}")

    if resolved_vars:
        log.info(f"成功解析 {len(resolved_vars)} 个配置变量")

    def _traverse_and_resolve(node: Any) -> Any:
        if isinstance(node, dict):
            return {k: _traverse_and_resolve(v) for k, v in node.items()}
        elif isinstance(node, list):
            return [_traverse_and_resolve(item) for item in node]
        elif isinstance(node, str):
            for name, value in resolved_vars.items():
                node = node.replace(f"${{{name}}}", str(value))

            node = os.path.expandvars(node)

            if "$(" in node:
                command = f'echo "{node}"'
                try:
                    return subprocess.check_output(command, shell=True, text=True).strip()
                except subprocess.CalledProcessError as e:
                    raise ConfigError(f"配置中的 shell 命令执行失败: {node}\n错误: {e}")
        return node

    return _traverse_and_resolve(config)


def load_workload_config(workload_specifier: str) -> dict:
    """
    加载并验证指定工作负载的 YAML 配置。
    'workload_specifier' 可以是一个名字（在 config/workloads/ 中查找），
    也可以是一个直接指向 .yaml 文件的路径。
    """
    project_root = get_project_root()
    potential_path = Path(workload_specifier)

    if potential_path.is_file() and potential_path.suffix in [".yaml", ".yml"]:
        config_path = potential_path
        log.info(f"直接从路径加载 workload 配置文件: {config_path}")
    else:
        config_path = project_root / f"config/workloads/{workload_specifier}.yaml"
        log.info(f"在默认目录中查找 workload: {config_path}")

    if not config_path.is_file():
        raise ConfigError(f"Workload 配置文件未找到: {config_path}")

    try:
        with open(config_path, "r") as f:
            raw_config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"解析 YAML 文件 {config_path} 出错: {e}")

    resolved_config = _resolve_variables_and_commands(raw_config)

    if not isinstance(resolved_config, dict):
        raise ConfigError("Workload 配置的顶层必须是一个字典。")

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
