import pandas as pd
from pipa.common.logger import logger
from pipa.common.utils import get_timestamp
from pipa.common.config import OUTPUT_DIR
import sqlite3


class SQLiteConnector:
    def __init__(self, db_path):
        self.db_path = db_path

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def fetch_table_as_dataframe(self, table_name):
        df = self.execute_query(f"SELECT * FROM {table_name}")
        logger.info(f"Table {table_name} fetched successfully.")
        return df

    def execute_query(self, query):
        with self._connect() as conn:
            df = pd.read_sql_query(query, conn)
        logger.info("Query executed successfully.")
        return df

    def execute_query_and_export_to_csv(self, query, output_filepath):
        df = self.execute_query(query)
        logger.info(f"Exporting query result to {output_filepath}")
        df.to_csv(output_filepath, index=False)
        return df

    def export_table_to_csv(self, table_name, output_filepath=None):
        output_filepath = output_filepath or f"{OUTPUT_DIR}/{table_name}.csv"
        df = self.fetch_table_as_dataframe(table_name)
        logger.info(f"Exporting table {table_name} to {output_filepath}")
        df.to_csv(output_filepath, index=False)
        return df

    def export_table_to_excel(self, table_name, output_filepath=None):
        output_filepath = output_filepath or f"{OUTPUT_DIR}/{table_name}.xlsx"
        df = self.fetch_table_as_dataframe(table_name)
        logger.info(f"Exporting table {table_name} to {output_filepath}")
        df.to_excel(output_filepath, index=False)
        return df


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
                output_filepath = filepath or f"{OUTPUT_DIR}/pipa_{get_timestamp()}.csv"
                logger.info(f"Exporting DataFrame to {output_filepath}")
                result.to_csv(output_filepath, index=False)
            return result

        return wrapper

    return decorator
