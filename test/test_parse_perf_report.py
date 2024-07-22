import pytest
from unittest.mock import mock_open
import pandas as pd
from pipa.parser.perf_report import parse_perf_report_file, parse_one_line


@pytest.fixture
def sample_data():
    return """
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


@pytest.fixture
def expected_df():
    data = {
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
    return pd.DataFrame(data)


def test_parse_perf_report_file(monkeypatch, sample_data, expected_df):
    # Mock file read
    mock_open_func = mock_open(read_data=sample_data)
    monkeypatch.setattr("builtins.open", mock_open_func)

    # Call the function
    result = parse_perf_report_file("./test_resources/perf.report")

    for col in result.columns:
        for i, (act, exp) in enumerate(zip(result[col], expected_df[col])):
            if act != exp:
                print(f"Column: {col}, Row: {i}, Actual: {act}, Expected: {exp}")

    # Compare the result with the expected DataFrame
    pd.testing.assert_frame_equal(result, expected_df)


@pytest.fixture
def test_line():
    return "    14.31%   2.91%  java             libjvm.so                                                           [.] SpinPause"


@pytest.fixture
def line_ranges():
    return [(4, 18), (20, 24), (37, 46), (105, -1)]


def test_parse_one_line(test_line, line_ranges):
    expected_output = (14.31, 2.91, "java", "libjvm.so", ".", "SpinPause")
    result = parse_one_line(test_line, line_ranges)
    assert result == expected_output


def test_parse_one_line_incorrect_format():
    incorrect_line = "incorrect format data"
    line_ranges = [(4, 18), (20, 24), (37, 46), (105, -1)]
    result = parse_one_line(incorrect_line, line_ranges)
    assert result is None


if __name__ == "__main__":
    pytest.main([__file__])
