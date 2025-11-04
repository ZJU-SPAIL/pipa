# src/logger_setup.py

import logging
import sys


def setup_logging(verbosity: int):
    """
    Configures the root logger for the application.
    为应用程序配置根日志记录器。

    :param verbosity: The verbosity level (0=WARNING, 1=INFO, 2=DEBUG).
    """
    log_level = logging.WARNING  # Default level
    if verbosity == 1:
        log_level = logging.INFO
    elif verbosity >= 2:
        log_level = logging.DEBUG

    # Get the root logger
    # 获取根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove any existing handlers to avoid duplicate logs
    # 移除任何已存在的处理器，以避免日志重复
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Create a handler to write to the console (stderr)
    # 创建一个写入到控制台 (stderr) 的处理器
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(log_level)

    # Create a formatter
    # 创建一个格式化器
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    # Add the handler to the root logger
    # 将处理器添加到根日志记录器
    root_logger.addHandler(handler)

    if verbosity >= 2:
        logging.debug("Debug logging enabled.")
