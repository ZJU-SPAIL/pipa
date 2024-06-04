import pandas as pd
from pipa.common.logger import logger
from pipa.common.utils import get_timestamp
from pipa.common.config import OUTPUT_DIR


def export_dataframe_to_csv(filepath=None):
    """
    Decorator function that exports a pandas DataFrame to a CSV file.

    Args:
        filepath (str, optional): The output file path. If not provided, a default path will be used.

    Returns:
        The decorated function.
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            if isinstance(result, pd.DataFrame):
                output_filepath = (
                    filepath or f"{OUTPUT_DIR}/export_{get_timestamp()}.csv"
                )
                logger.info(f"Exporting DataFrame to {output_filepath}")
                result.to_csv(output_filepath, index=False)
            return result

        return wrapper

    return decorator
