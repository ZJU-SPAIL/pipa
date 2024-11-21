import datetime
from math import sqrt
import sys
from typing import Tuple, List
from rich import print


def find_closest_factor_pair(n: int) -> Tuple[int, int]:
    """
    Find closest factor pair of n

    Args:
        n (int): number to find

    Returns:
        Tuple[int, int]: (small factor A, large factor B), A * B = n
    """
    for i in range(int(sqrt(n)), 0, -1):
        if n % i == 0:
            return (i, n // i)


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
        except KeyboardInterrupt as e:
            # Print "Cancelled by user" and exit
            print("Cancelled by user")
            sys.exit(0)
        except TypeError as e:
            sys.exit(0)

    return wrapper


def generate_unique_rgb_color(data: List) -> Tuple[int, int, int]:
    """
    Generate unique RGB color from data

    Args:
        data (Tuple): Generate rgb from hash of data

    Returns:
        Tuple[int, int, int]: rgb color, (r, g, b)
    """
    # generate hash
    data_hash = hash(tuple(data))

    r = (data_hash & 0xFF0000) >> 16
    g = (data_hash & 0x00FF00) >> 8
    b = data_hash & 0x0000FF

    r = r % 256
    g = g % 256
    b = b % 256

    return (r, g, b)
