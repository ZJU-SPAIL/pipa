import os
from pipa.common.config import ALL_PATH
from pipa.common.logger import logger
from pipa.export_config.all import get_all_config


def create_directories():
    # Create the directories
    for path in ALL_PATH:
        os.makedirs(path, exist_ok=True)
        logger.info(f"Directory created: {path}")
    logger.info("All directories created successfully.")


def get_config():
    get_all_config()
    logger.info("System configuration exported successfully.")


if __name__ == "__main__":
    create_directories()
    get_config()
