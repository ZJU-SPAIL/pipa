import pytest
import pandas as pd
from pipa.parser.sar import (
    trans_time_to_seconds,
    merge_one_line,
    add_post_fix,
    split_sar_block,
    parse_sar_string,
    SarDataIndex,
)


# Test for trans_time_to_seconds
def test_trans_time_to_seconds():
    tas = [
        (["12:00:00", "12:00:01", "12:00:02"], [0.0, 1.0, 2.0]),
        (["23:59:59", "00:00:00", "00:00:01"], [0.0, 1.0, 2.0]),
        (["23:59:59"], [0.0]),
        ([], []),
        (["23:59:59", "00:00:00", "00:00:00"], [0.0, 1.0, 1.0]),
        (
            ["23:59:59", "00:00:00", "00:00:01", "00:00:00"],
            [0.0, 1.0, 2.0, 86401.0],
        ),
    ]
    for ta in tas:
        t, e = ta
        data = {"timestamp": t}
        df = pd.DataFrame(data)
        result = trans_time_to_seconds(df.copy())
        expected = pd.DataFrame({"timestamp": e})
        pd.testing.assert_frame_equal(result, expected)


# Test for avg_metric_to_all_metric
def test_avg_metric_to_all_metric():
    e1 = SarDataIndex.avg_metric_to_all_metric(SarDataIndex.AvgCPUFreq)
    assert e1 == SarDataIndex.CPUFreq
    e2 = SarDataIndex.avg_metric_to_all_metric(SarDataIndex.AvgCPUUtils)
    assert e2 == SarDataIndex.CPUUtils


# Test for merge_one_line
@pytest.mark.parametrize(
    "sar_line, expected",
    [
        (
            "12:00:00 AM CPU all 0.12 0.00 0.06 0.00 0.00 99.82",
            ["12:00:00", "CPU", "all", "0.12", "0.00", "0.06", "0.00", "0.00", "99.82"],
        ),
        (
            "12:00:00 PM CPU all 0.12 0.00 0.06 0.00 0.00 99.82",
            ["12:00:00", "CPU", "all", "0.12", "0.00", "0.06", "0.00", "0.00", "99.82"],
        ),
    ],
)
def test_merge_one_line(sar_line, expected):
    result = merge_one_line(sar_line)
    assert result == expected


# Test for add_post_fix
@pytest.mark.parametrize(
    "sar_line, len_columns, expected",
    [
        (
            ["12:00:00", "CPU", "all", "0.12", "0.00", "0.06"],
            9,
            ["12:00:00", "CPU", "all", "0.12", "0.00", "0.06", "", "", ""],
        ),
        (
            ["12:00:00", "CPU", "all", "0.12", "0.00", "0.06", "extra", "values"],
            6,
            ["12:00:00", "CPU", "all", "0.12", "0.00", "0.06extra values"],
        ),
    ],
)
def test_add_post_fix(sar_line, len_columns, expected):
    result = add_post_fix(sar_line, len_columns)
    assert result == expected


# Test for split_sar_block
@pytest.mark.parametrize(
    "lines, expected",
    [
        (
            ["line 1\n", "line 2\n", "\n", "line 3\n", "\n", "line 4\n"],
            [["line 1", "line 2"], ["line 3"], ["line 4"]],
        ),
        (
            ["line 1\n", "line 2\n", "\n", "\n", "line 3\n", "\n", "line 4\n"],
            [["line 1", "line 2"], ["line 3"], ["line 4"]],
        ),
        (["line 1\n", "\n"], [["line 1"]]),
        ([], [[]]),
        (["line 1\n", "line 2\n", "line 3\n"], [["line 1", "line 2", "line 3"]]),
    ],
)
def test_split_sar_block(lines, expected):
    result = split_sar_block(lines)
    assert result == expected


# Test for parse_sar_string
def test_parse_sar_string():
    sar_string = """
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
    expected_df = pd.DataFrame(
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

    result = parse_sar_string(sar_string.strip().split("\n"))
    assert isinstance(result, list)
    assert len(result) == 1
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
        result_df.reset_index(drop=True), expected_df.reset_index(drop=True)
    )


if __name__ == "__main__":
    pytest.main([__file__])
