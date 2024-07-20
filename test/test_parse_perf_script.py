import unittest
from unittest.mock import patch, mock_open
from io import StringIO
import pandas as pd
from pipa.parser.perf_script import parse_perf_script_file, parse_one_line
from pipa.common.logger import logger


class TestParsePerfScriptFile(unittest.TestCase):
    def setUp(self):
        self.sample_perf_script = """
# missing features: TRACING_DATA BRANCH_STACK AUXTRACE STAT CLOCKID DIR_FORMAT COMPRESSED CLOCK_DATA HYBRID_TOPOLOGY HYBRID_CPU_PMU_CAPS 
# ========
#
            perf 3732494 [000] 954453.309835:       2715       cycles:  ffffffff8ae9ceb6 native_write_msr+0x6 ([kernel.kallsyms])
            perf 3732494 [000] 954453.309835:        380 instructions:  ffffffff8ae9ceb6 native_write_msr+0x6 ([kernel.kallsyms])
            perf 3732494 [001] 954453.310054:       2034       cycles:  ffffffff8ae9ceb6 native_write_msr+0x6 ([kernel.kallsyms])
            perf 3732494 [001] 954453.310054:        380 instructions:  ffffffff8ae9ceb6 native_write_msr+0x6 ([kernel.kallsyms])
            perf 3732494 [002] 954453.310232:       1874       cycles:  ffffffff8ae9ceb6 native_write_msr+0x6 ([kernel.kallsyms])
        """
        self.expected_data = pd.DataFrame(
            {
                "command": ["perf", "perf", "perf", "perf", "perf"],
                "pid": [3732494, 3732494, 3732494, 3732494, 3732494],
                "cpu": [0, 0, 1, 1, 2],
                "time": [
                    "954453.309835",
                    "954453.309835",
                    "954453.310054",
                    "954453.310054",
                    "954453.310232",
                ],
                "value": [2715, 380, 2034, 380, 1874],
                "event": ["cycles", "instructions", "cycles", "instructions", "cycles"],
                "addr": [
                    "ffffffff8ae9ceb6",
                    "ffffffff8ae9ceb6",
                    "ffffffff8ae9ceb6",
                    "ffffffff8ae9ceb6",
                    "ffffffff8ae9ceb6",
                ],
                "symbol": [
                    "native_write_msr+0x6",
                    "native_write_msr+0x6",
                    "native_write_msr+0x6",
                    "native_write_msr+0x6",
                    "native_write_msr+0x6",
                ],
                "dso_short_name": [
                    "[kernel.kallsyms]",
                    "[kernel.kallsyms]",
                    "[kernel.kallsyms]",
                    "[kernel.kallsyms]",
                    "[kernel.kallsyms]",
                ],
            }
        )

    @patch("builtins.open", new_callable=mock_open, read_data="")
    @patch("os.path.exists", return_value=True)
    def test_parse_perf_script_file(self, mock_exists, mock_open):
        mock_open.return_value = StringIO(self.sample_perf_script)

        # Call the function with the mocked data
        result_df = parse_perf_script_file("dummy_path")

        # Check if the resulting DataFrame matches the expected data
        pd.testing.assert_frame_equal(result_df, self.expected_data)


class TestParseOneLine(unittest.TestCase):
    def setUp(self):
        self.test_line = "            perf 3732494 [000] 954453.309835:       2715       cycles:  ffffffff8ae9ceb6 native_write_msr+0x6 ([kernel.kallsyms])"
        self.expected_output = [
            "perf",
            3732494,
            0,
            "954453.309835",
            2715,
            "cycles",
            "ffffffff8ae9ceb6",
            "native_write_msr+0x6",
            "[kernel.kallsyms]",
        ]

    @patch.object(
        logger, "warning"
    )  # Mocking logger.warning to avoid actual logging during tests
    def test_parse_one_line(self, mock_warning):
        result = parse_one_line(self.test_line)
        self.assertEqual(result, self.expected_output)

    def test_parse_one_line_invalid_format(self):
        invalid_line = "invalid format line"
        result = parse_one_line(invalid_line)
        self.assertIsNone(result)


def run_test_parse_perf_script_file():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestParsePerfScriptFile)
    result = unittest.TextTestRunner().run(suite)
    return result


def run_test_parse_one_line():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestParseOneLine)
    result = unittest.TextTestRunner().run(suite)
    return result


if __name__ == "__main__":
    result1 = run_test_parse_perf_script_file()
    #print("TestParsePerfScriptFile Results:", result1)

    result2 = run_test_parse_one_line()
    #print("TestParseOneLine Results:", result2)
