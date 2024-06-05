import questionary
from pipa.export_config.cpu_config import get_cpu_cores
from rich import print


def ask_number(question: str, default: int) -> int:
    """
    Asks the user to input a number based on the given question and default value.

    Args:
        question (str): The question to ask the user.
        default (int): The default value to return if the user doesn't input anything.

    Returns:
        int: The number inputted by the user or the default value.
    """
    result = questionary.text(question).ask().strip()
    if result == "":
        return default
    elif result.isdigit():
        return int(result)
    else:
        print("Please input a number.")
        exit(1)


CORES_ALL = get_cpu_cores()
