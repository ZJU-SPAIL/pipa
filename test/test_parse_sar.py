import unittest
import pandas as pd
from pipa.parser.sar import (
    trans_time_to_seconds,
    trans_time_to_24h,
    merge_one_line,
    add_post_fix,
    split_sar_block,
    parse_sar_string,
)


class TestTransTimeToSeconds(unittest.TestCase):
    def setUp(self):
        self.data = {"timestamp": ["12:00:00", "12:00:01", "12:00:02"]}
        self.df = pd.DataFrame(self.data)

    def test_trans_time_to_seconds(self):
        result = trans_time_to_seconds(self.df.copy())
        expected = pd.DataFrame({"timestamp": [0.0, 1.0, 2.0]})
        pd.testing.assert_frame_equal(result, expected)


class TestTransTimeTo24h(unittest.TestCase):
    def test_trans_time_to_24h_am(self):
        time_str = "10:00:00 AM"
        result = trans_time_to_24h(time_str)
        expected = "10:00:00"
        self.assertEqual(result, expected)

    def test_trans_time_to_24h_pm(self):
        time_str = "10:00:00 PM"
        result = trans_time_to_24h(time_str)
        expected = "22:00:00"
        self.assertEqual(result, expected)


class TestMergeOneLine(unittest.TestCase):
    def test_merge_one_line_am(self):
        sar_line = "12:00:00 AM CPU all 0.12 0.00 0.06 0.00 0.00 99.82"
        result = merge_one_line(sar_line)
        expected = [
            "12:00:00",
            "CPU",
            "all",
            "0.12",
            "0.00",
            "0.06",
            "0.00",
            "0.00",
            "99.82",
        ]
        self.assertEqual(result, expected)

    def test_merge_one_line_pm(self):
        sar_line = "12:00:00 PM CPU all 0.12 0.00 0.06 0.00 0.00 99.82"
        result = merge_one_line(sar_line)
        expected = [
            "12:00:00",
            "CPU",
            "all",
            "0.12",
            "0.00",
            "0.06",
            "0.00",
            "0.00",
            "99.82",
        ]
        self.assertEqual(result, expected)


class TestAddPostFix(unittest.TestCase):
    def test_add_post_fix(self):
        sar_line = ["12:00:00", "CPU", "all", "0.12", "0.00", "0.06"]
        len_columns = 9
        result = add_post_fix(sar_line, len_columns)
        expected = ["12:00:00", "CPU", "all", "0.12", "0.00", "0.06", "", "", ""]
        self.assertEqual(result, expected)

    def test_add_post_fix_longer(self):
        sar_line = ["12:00:00", "CPU", "all", "0.12", "0.00", "0.06", "extra", "values"]
        len_columns = 6
        result = add_post_fix(sar_line, len_columns)
        expected = ["12:00:00", "CPU", "all", "0.12", "0.00", "0.06extra values"]
        self.assertEqual(result, expected)


class TestSplitSarBlock(unittest.TestCase):
    def test_split_sar_block(self):
        # Test splitting a block with multiple lines
        lines = ["line 1\n", "line 2\n", "\n", "line 3\n", "\n", "line 4\n"]
        expected_output = [["line 1", "line 2"], ["line 3"], ["line 4"]]
        self.assertEqual(split_sar_block(lines), expected_output)

        # Test splitting a block with multiple '\n'
        lines = ["line 1\n", "line 2\n", "\n", "\n", "line 3\n", "\n", "line 4\n"]
        expected_output = [["line 1", "line 2"], ["line 3"], ["line 4"]]
        self.assertEqual(split_sar_block(lines), expected_output)

        # Test splitting a block with a single line
        lines = ["line 1\n", "\n"]
        expected_output = [["line 1"]]
        self.assertEqual(split_sar_block(lines), expected_output)

        # Test splitting an empty block
        lines = []
        expected_output = [[]]
        self.assertEqual(split_sar_block(lines), expected_output)

        # Test splitting a block with no empty lines
        lines = ["line 1\n", "line 2\n", "line 3\n"]
        expected_output = [["line 1", "line 2", "line 3"]]
        self.assertEqual(split_sar_block(lines), expected_output)


class TestParseSarString(unittest.TestCase):
    def setUp(self):
        self.sar_string = """
Linux 5.15.0-113-generic (black)    07/15/24    _x86_64_    (160 CPU)

19:53:36        CPU      %usr     %nice      %sys   %iowait    %steal      %irq     %soft    %guest    %gnice     %idle
19:53:37        all      4.32      0.00      0.90      0.03      0.00      0.00      0.01      0.00      0.00     94.74
19:53:37          0      4.12      0.00     11.34      0.00      0.00      0.00      0.00      0.00      0.00     84.54
19:53:37          1      0.00      0.00      1.03      0.00      0.00      0.00      0.00      0.00      0.00     98.97
19:53:37          2      2.04      0.00      0.00      0.00      0.00      0.00      0.00      0.00      0.00     97.96
19:53:37          3      0.00      0.00      0.00      0.00      0.00      0.00      0.00      0.00      0.00    100.00
19:53:37          4      4.08      0.00      0.00      0.00      0.00      0.00      0.00      0.00      0.00     95.92
19:53:37          5      7.00      0.00      0.00      0.00      0.00      0.00      0.00      0.00      0.00     93.00
19:53:37          6      6.06      0.00      0.00      0.00      0.00      0.00      0.00      0.00      0.00     93.94
19:53:37          7      7.07      0.00      0.00      0.00      0.00      0.00      0.00      0.00      0.00     92.93
        """
        self.expected_df = pd.DataFrame(
            {
                "timestamp": ["19:53:37"] * 9,
                "CPU": ["all", "0", "1", "2", "3", "4", "5", "6", "7"],
                "%usr": [4.32, 4.12, 0.00, 2.04, 0.00, 4.08, 7.00, 6.06, 7.07],
                "%nice": [0.00] * 9,
                "%sys": [0.90, 11.34, 1.03, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
                "%iowait": [0.03, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
                "%steal": [0.00] * 9,
                "%irq": [0.00] * 9,
                "%soft": [0.01, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
                "%guest": [0.00] * 9,
                "%gnice": [0.00] * 9,
                "%idle": [
                    94.74,
                    84.54,
                    98.97,
                    97.96,
                    100.00,
                    95.92,
                    93.00,
                    93.94,
                    92.93,
                ],
            }
        )

    def test_parse_sar_string(self):
        result = parse_sar_string(self.sar_string.strip().split("\n"))

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        result_df = result[0]

        float_columns = [
            "%usr",
            "%nice",
            "%sys",
            "%iowait",
            "%steal",
            "%irq",
            "%soft",
            "%guest",
            "%gnice",
            "%idle",
        ]
        result_df[float_columns] = result_df[float_columns].astype(float)

        pd.testing.assert_frame_equal(
            result_df.reset_index(drop=True), self.expected_df.reset_index(drop=True)
        )


if __name__ == "__main__":
    unittest.main()
