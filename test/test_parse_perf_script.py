import pytest
from unittest.mock import mock_open
import pandas as pd
from pipa.parser.perf_script import parse_perf_script_file, parse_one_line
from pipa.common.logger import logger


@pytest.fixture
def sample_perf_script():
    return """
# ========
#
            perf 3732494 [000] 954453.309835:       2715       cycles:  ffffffff8ae9ceb6 native_write_msr+0x6 ([kernel.kallsyms])
            perf 3732494 [000] 954453.309835:        380 instructions:  ffffffff8ae9ceb6 native_write_msr+0x6 ([kernel.kallsyms])
            perf 3732494 [001] 954453.310054:       2034       cycles:  ffffffff8ae9ceb6 native_write_msr+0x6 ([kernel.kallsyms])
            perf 3732494 [001] 954453.310054:        380 instructions:  ffffffff8ae9ceb6 native_write_msr+0x6 ([kernel.kallsyms])
            perf 3732494 [002] 954453.310232:       1874       cycles:  ffffffff8ae9ceb6 native_write_msr+0x6 ([kernel.kallsyms])
        """


@pytest.fixture
def expected_data():
    return pd.DataFrame(
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


def test_parse_perf_script_file(monkeypatch, sample_perf_script, expected_data):
    monkeypatch.setattr("builtins.open", mock_open(read_data=""))
    monkeypatch.setattr("os.path.exists", lambda x: True)
    open_mock = mock_open(read_data=sample_perf_script)
    monkeypatch.setattr("builtins.open", open_mock)

    # Call the function with the mocked data
    result_df = parse_perf_script_file("dummy_path")

    # Check if the resulting DataFrame matches the expected data
    pd.testing.assert_frame_equal(result_df, expected_data)


@pytest.fixture
def test_line():
    return "            perf 3732494 [000] 954453.309835:       2715       cycles:  ffffffff8ae9ceb6 native_write_msr+0x6 ([kernel.kallsyms])"


@pytest.fixture
def expected_output():
    return [
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


def test_parse_one_line(monkeypatch, test_line, expected_output):
    monkeypatch.setattr(logger, "warning", lambda msg: None)  # Mocking logger.warning
    result = parse_one_line(test_line)
    assert result == expected_output


def test_parse_one_line_invalid_format(monkeypatch):
    invalid_line = "invalid format line"
    result = parse_one_line(invalid_line)
    assert result is None


if __name__ == "__main__":
    pytest.main([__file__])
