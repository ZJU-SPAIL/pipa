import unittest
import os
import pandas as pd
from unittest.mock import patch, MagicMock
from pipa.common.export import SQLiteConnector, export_dataframe_to_csv


class TestSQLiteConnector(unittest.TestCase):
    def setUp(self):
        self.db_path = ":memory:"
        self.connector = SQLiteConnector(self.db_path)
        self.test_df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})

    @patch("sqlite3.connect")
    def test_fetch_table_as_dataframe(self, mock_connect):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.__enter__.return_value.cursor.return_value.execute.return_value = None
        mock_conn.__enter__.return_value.cursor.return_value.fetchall.return_value = [
            (1, 4),
            (2, 5),
            (3, 6),
        ]
        mock_conn.__enter__.return_value.cursor.return_value.description = [
            ("A",),
            ("B",),
        ]

        result = self.connector.fetch_table_as_dataframe("test_table")
        self.assertTrue(isinstance(result, pd.DataFrame))
        self.assertEqual(result.shape, (3, 2))

    @patch("sqlite3.connect")
    def test_execute_query(self, mock_connect):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.__enter__.return_value.cursor.return_value.execute.return_value = None
        mock_conn.__enter__.return_value.cursor.return_value.fetchall.return_value = [
            (1, 4),
            (2, 5),
            (3, 6),
        ]
        mock_conn.__enter__.return_value.cursor.return_value.description = [
            ("A",),
            ("B",),
        ]

        result = self.connector.execute_query("SELECT * FROM test_table")
        self.assertTrue(isinstance(result, pd.DataFrame))
        self.assertEqual(result.shape, (3, 2))

    @patch("sqlite3.connect")
    def test_export_table_to_csv(self, mock_connect):
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.__enter__.return_value.cursor.return_value.execute.return_value = None
        mock_conn.__enter__.return_value.cursor.return_value.fetchall.return_value = [
            (1, 4),
            (2, 5),
            (3, 6),
        ]
        mock_conn.__enter__.return_value.cursor.return_value.description = [
            ("A",),
            ("B",),
        ]

        output_file = "test_output.csv"
        self.connector.export_table_to_csv("test_table", output_file)
        self.assertTrue(os.path.exists(output_file))
        os.remove(output_file)


class TestExportDataframeToCSV(unittest.TestCase):
    def test_export_dataframe_to_csv(self):
        @export_dataframe_to_csv("test_output.csv")
        def dummy_function():
            return pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})

        dummy_function()
        self.assertTrue(os.path.exists("test_output.csv"))
        df = pd.read_csv("test_output.csv")
        self.assertEqual(df.shape, (3, 2))
        self.assertTrue(df.equals(pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})))
        os.remove("test_output.csv")


if __name__ == "__main__":
    unittest.main()
