import logging
import time
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

# Create a stream handler and set its level
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(formatter)

# Add file handler
file_handler = logging.FileHandler('pipa.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(stream_handler)
logger.addHandler(file_handler)


def set_level(
    logger_level: Optional[str | int] = None, print_level: Optional[str | int] = None
):
    try:
        if logger_level:
            logger.setLevel(logger_level)
        if print_level:
            stream_handler.setLevel(print_level)
    except Exception as e:
        logger.warning(f"{e}")
        logger.warning(
            f"available logger levels: {','.join(logging.getLevelNamesMapping().keys())}"
        )
        logger.warning(f"use logger level: {logging.getLevelName(logger.level)}")
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
            logger.error(f"Function {func.__name__} failed with error: {str(e)}", exc_info=True)
            raise
        finally:
            end_time = time.time()
            logger.info(f"Function {func.__name__} execution time: {end_time - start_time:.4f} seconds")
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