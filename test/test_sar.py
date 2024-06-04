from pipa.parser.sar import split_sar_block
import pytest


def test_split_sar_block():
    # Test splitting a block with multiple lines
    lines = ["line 1\n", "line 2\n", "\n", "line 3\n", "\n", "line 4\n"]
    expected_output = [["line 1", "line 2"], ["line 3"], ["line 4"]]
    assert split_sar_block(lines) == expected_output

    # Test splitting a block with multiple '\n'
    lines = ["line 1\n", "line 2\n", "\n", "\n", "line 3\n", "\n", "line 4\n"]
    expected_output = [["line 1", "line 2"], ["line 3"], ["line 4"]]
    assert split_sar_block(lines) == expected_output

    # Test splitting a block with a single line
    lines = ["line 1\n", "\n"]
    expected_output = [["line 1"]]
    assert split_sar_block(lines) == expected_output

    # Test splitting an empty block
    lines = []
    expected_output = [[]]
    assert split_sar_block(lines) == expected_output

    # Test splitting a block with no empty lines
    lines = ["line 1\n", "line 2\n", "line 3\n"]
    expected_output = [["line 1", "line 2", "line 3"]]
    assert split_sar_block(lines) == expected_output


if __name__ == "__main__":
    pytest.main([__file__])
