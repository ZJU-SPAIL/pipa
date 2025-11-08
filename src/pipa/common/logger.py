import logging
import os
import platform
import time
from pathlib import Path
from functools import wraps
from typing import Optional

# Create a logger
logger = logging.getLogger(__name__)

# Set the logging level, it's the minimum acceptable level
logger.setLevel(logging.INFO)

# Create formatters with more context information
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(module)s:%(funcName)s:%(lineno)d - %(levelname)s - %(message)s"
)


def _default_log_dir() -> Path:
    # Allow override via environment variable
    override = os.getenv("PIPA_LOG_DIR")
    if override:
        return Path(override).expanduser()

    system = platform.system().lower()
    home = Path.home()
    if system == "darwin":
        return home / "Library" / "Logs" / "pipa"
    if system == "windows":
        base = os.getenv("LOCALAPPDATA") or (home / "AppData" / "Local")
        return Path(base) / "pipa" / "Logs"
    # Linux/Unix: follow XDG base dirs where possible
    xdg_state = os.getenv("XDG_STATE_HOME")
    if xdg_state:
        return Path(xdg_state) / "pipa"
    # Fallback to ~/.local/state/pipa
    return home / ".local" / "state" / "pipa"


# Ensure handlers are added only once (avoid duplicates on re-import)
if not logger.handlers:
    # Create a stream handler and set its level
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(formatter)

    # Prepare file handler path
    log_dir = _default_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "pipa.log"

    # Create file handler
    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Add handlers to logger
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
else:
    # If handlers exist, try to find stream handler for set_level
    stream_handler = next((h for h in logger.handlers if isinstance(h, logging.StreamHandler)), None)


def set_level(
    logger_level: Optional[str | int] = None, print_level: Optional[str | int] = None
):
    try:
        if logger_level is not None:
            logger.setLevel(logger_level)
        if print_level is not None and stream_handler is not None:
            stream_handler.setLevel(print_level)
    except Exception as e:
        logger.warning(f"{e}")
        try:
            avail = ",".join(logging.getLevelNamesMapping().keys())
        except Exception:
            avail = "CRITICAL,ERROR,WARNING,INFO,DEBUG,NOTSET"
        logger.warning(f"available logger levels: {avail}")
        logger.warning(f"use logger level: {logging.getLevelName(logger.level)}")
        if stream_handler is not None:
            logger.warning(f"use print level: {logging.getLevelName(stream_handler.level)}")


def log_execution(func):
    """Decorator to log function execution details"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"Executing function: {func.__name__}")
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            logger.info(f"Function {func.__name__} executed successfully")
            return result
        except Exception as e:
            logger.error(
                f"Function {func.__name__} failed with error: {str(e)}", exc_info=True
            )
            raise
        finally:
            end_time = time.time()
            logger.info(
                f"Function {func.__name__} execution time: {end_time - start_time:.4f} seconds"
            )

    return wrapper


if __name__ == "__main__":
    # Example usage of log_execution decorator
    @log_execution
    def test_function():
        logger.debug("Debug message")
        logger.info("Info message")
        time.sleep(0.5)
        return "Success"

    test_function()
    # Example usage
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
