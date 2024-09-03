import datetime
from math import sqrt
import sys
from typing import Tuple
from rich import print


def find_closet_factor_pair(n: int) -> Tuple[int, int]:
    """
    Find closet fator pair of n

    Args:
        n (int): number to find

    Returns:
        Tuple[int, int]: (small factor A, large factor B), A * B = n
    """
    m = int(sqrt(n))
    while n % m != 0:
        m -= 1
    return (m, int(n / m))


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
