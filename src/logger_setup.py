# src/logger_setup.py

import logging
import sys


def setup_logging(verbosity: int):
    """
    Configures the root logger for the application.
    为应用程序配置根日志记录器。

    :param verbosity: The verbosity level (0=WARNING, 1=INFO, 2=DEBUG).
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
