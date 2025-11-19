"""
日志设置模块

此模块负责配置应用程序的日志记录系统。
根据详细程度参数设置适当的日志级别和格式。
"""

import logging
import sys


def setup_logging(verbosity: int):
    """
    为应用程序配置根日志记录器。

    根据详细程度参数设置日志级别：
    - 0: WARNING级别
    - 1: INFO级别
    - 2及以上: DEBUG级别

    配置流处理器输出到stderr，使用标准格式。

    参数:
        verbosity: 详细程度级别（0=WARNING, 1=INFO, 2=DEBUG）。
    """
    log_level = logging.WARNING
    if verbosity == 1:
        log_level = logging.INFO
    elif verbosity >= 2:
        log_level = logging.DEBUG

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(log_level)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    root_logger.addHandler(handler)

    if verbosity >= 2:
        logging.debug("Debug logging enabled.")
