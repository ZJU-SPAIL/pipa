import datetime
import sys
from pipa.common.logger import logger
from rich import print


def get_timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")


def handle_user_cancelled(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            # Print "Cancelled by user" and exit
            print("Cancelled by user")
            sys.exit(0)

    return wrapper
