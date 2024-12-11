import logging
from typing import Optional

# Create a logger
logger = logging.getLogger(__name__)

# Set the logging level, it's the minimum acceptable level
logger.setLevel(logging.INFO)

# Create a stream handler and set its level
# it's the minimum level that can be output
# set to ERROR since print will slow down the process
# use DEBUG, INFO, WARNING at most of the time
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.ERROR)

# Create a formatter and add it to the stream handler
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
stream_handler.setFormatter(formatter)

# Add the stream handler to the logger
logger.addHandler(stream_handler)


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


if __name__ == "__main__":
    # Example usage
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
