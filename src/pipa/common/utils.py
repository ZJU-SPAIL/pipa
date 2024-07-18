import datetime
import sys
from rich import print


def get_timestamp():
    """
    Returns the current timestamp in the format "YYYY-MM-DD-HH-MM-SS".

    Returns:
        str: The current timestamp.
    """
    return datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")


def handle_user_cancelled(func):
    """
    Decorator function that handles user cancellation by catching the KeyboardInterrupt exception.

    Args:
        func: The function to be decorated.

    Returns:
        The decorated function.

    Raises:
        None.
    """

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            # Print "Cancelled by user" and exit
            print("Cancelled by user")
            sys.exit(0)

    return wrapper
