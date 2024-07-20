import unittest
from unittest.mock import mock_open, patch
import pandas as pd
from pipa.parser.perf_report import parse_perf_report_file, parse_one_line
from io import StringIO


class TestParsePerfReportFile(unittest.TestCase):

    def setUp(self):
        # Set up sample data and file path
        self.sample_data = """
#         Overhead  Command          Shared Object                                                       Symbol
# ................  ...............  ..................................................................  ..................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................................
#
    14.31%   2.91%  java             libjvm.so                                                           [.] SpinPause
     7.10%   3.77%  swapper          [kernel.kallsyms]                                                   [k] mwait_idle_with_hints.constprop.0
     2.08%   0.43%  java             libjvm.so                                                           [.] ParallelTaskTerminator::offer_termination
     1.78%   2.71%  perf             perf                                                                [.] append_chain_children
     1.43%   3.06%  node             watcher.node                                                        [.] std::__detail::_Executor<__gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::allocator<std::__cxx11::sub_match<__gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > > >, std::cxx11::regex_traits<char>, true>::_M_dfs
     1.09%   2.34%  node             watcher.node                                                        [.] std::__detail::_Executor<__gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::allocator<std::__cxx11::sub_match<__gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > > >, std::__cxx11::regex_traits<char>, true>::_M_lookahead
     0.95%   0.41%  java             libjvm.so                                                           [.] GenericTaskQueueSet<OverflowTaskQueue<StarTask, (MemoryType)5, 131072u>, (MemoryType)5>::steal_best_of_2
     0.79%   1.18%  htop             [kernel.kallsyms]                                                   [k] __d_lookup_rcu
        """
        self.file_path = "./test_resources/perf.report"

    @patch("builtins.open", new_callable=mock_open, read_data=None)
    def test_parse_perf_report_file(self, mock_file):
        # Mock file read
        mock_file().readlines.return_value = self.sample_data.strip().split("\n")

        # Call the function
        result = parse_perf_report_file(self.file_path)

        # Define the expected DataFrame
        expected_data = {
            "overhead_cycles": [14.31, 7.10, 2.08, 1.78, 1.43, 1.09, 0.95, 0.79],
            "overhead_insns": [2.91, 3.77, 0.43, 2.71, 3.06, 2.34, 0.41, 1.18],
            "command": [
                "java",
                "swapper",
                "java",
                "perf",
                "node",
                "node",
                "java",
                "htop",
            ],
            "shared_object": [
                "libjvm.so",
                "[kernel.kallsyms]",
                "libjvm.so",
                "perf",
                "watcher.node",
                "watcher.node",
                "libjvm.so",
                "[kernel.kallsyms]",
            ],
            "execution_mode": [".", "k", ".", ".", ".", ".", ".", "k"],
            "symbol": [
                "SpinPause",
                "mwait_idle_with_hints.constprop.0",
                "ParallelTaskTerminator::offer_termination",
                "append_chain_children",
                "std::__detail::_Executor<__gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::allocator<std::__cxx11::sub_match<__gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > > >, std::cxx11::regex_traits<char>, true>::_M_dfs",
                "std::__detail::_Executor<__gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > >, std::allocator<std::__cxx11::sub_match<__gnu_cxx::__normal_iterator<char const*, std::__cxx11::basic_string<char, std::char_traits<char>, std::allocator<char> > > > >, std::__cxx11::regex_traits<char>, true>::_M_lookahead",
                "GenericTaskQueueSet<OverflowTaskQueue<StarTask, (MemoryType)5, 131072u>, (MemoryType)5>::steal_best_of_2",
                "__d_lookup_rcu",
            ],
        }
        expected_df = pd.DataFrame(expected_data)

        # Compare the result with the expected DataFrame
        pd.testing.assert_frame_equal(result, expected_df)


class TestParseOneLine(unittest.TestCase):

    def setUp(self):
        self.line = "    14.31%   2.91%  java             libjvm.so                                                           [.] SpinPause"
        self.lr = [(4, 18), (20, 24), (37, 46), (105, -1)]

    def test_parse_one_line(self):
        expected_output = (14.31, 2.91, "java", "libjvm.so", ".", "SpinPause")

        result = parse_one_line(self.line, self.lr)
        self.assertEqual(result, expected_output)

    def test_parse_one_line_incorrect_format(self):
        incorrect_line = "incorrect format data"
        result = parse_one_line(incorrect_line, self.lr)
        self.assertIsNone(result)


def run_test_parse_one_line():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestParseOneLine)
    result = unittest.TextTestRunner().run(suite)
    return result


def run_test_parse_perf_report_file():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestParsePerfReportFile)
    result = unittest.TextTestRunner().run(suite)
    return result


if __name__ == "__main__":
    result1 = run_test_parse_one_line()
    #print("TestParseOneLine Results:", result1)

    result2 = run_test_parse_perf_report_file()
    #print("TestParsePerfReportFile Results:", result2)
