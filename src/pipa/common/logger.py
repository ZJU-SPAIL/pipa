import logging

# Create a logger
logger = logging.getLogger(__name__)

# Set the logging level
logger.setLevel(logging.INFO)

# Create a stream handler and set its level
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.WARNING)

# Create a formatter and add it to the stream handler
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
stream_handler.setFormatter(formatter)

# Add the stream handler to the logger
logger.addHandler(stream_handler)

if __name__ == "__main__":
    # Example usage
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")
