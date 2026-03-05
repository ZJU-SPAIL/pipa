import pandas as pd
import io  # 导入 io 模块
from pipa.parser.perf_stat import PerfStatData, PerfStatParser
import pytest


# 我们把测试数据定义为一个多行字符串
MODERN_PERF_STAT_DATA = """
# Test data for modern perf stat format
1.000,CPU0,1000,,cycles:D,1000,100.00,,
1.000,CPU1,1200,,cycles:D,1000,100.00,,
1.000,CPU0,500,,instructions:D,1000,100.00,0.50,insn per cycle
1.000,CPU1,800,,instructions:D,1000,100.00,0.67,insn per cycle
1.000,CPU0,900,,ref-cycles:D,1000,100.00,,
1.000,CPU1,1100,,ref-cycles:D,1000,100.00,,
2.000,CPU0,1100,,cycles:D,1000,100.00,,
2.000,CPU1,1300,,cycles:D,1000,100.00,,
2.000,CPU0,550,,instructions:D,1000,100.00,0.50,insn per cycle
2.000,CPU1,880,,instructions:D,1000,100.00,0.68,insn per cycle
2.000,CPU0,1000,,ref-cycles:D,1000,100.00,,
2.000,CPU1,1200,,ref-cycles:D,1000,100.00,,
"""


def test_parse_perf_stat_file_with_modern_format_from_string():
    """
    Tests if the parser can correctly handle modern perf stat output,
    passed as a string buffer, which includes varying column counts.
    """
    # 1. Action: 将字符串伪装成文件，然后调用我们要测试的函数
    # io.StringIO 会创建一个“内存中的文本文件”
    string_io_buffer = io.StringIO(MODERN_PERF_STAT_DATA)
    df = PerfStatParser.parse_perf_stat_file(string_io_buffer)

    # 2. Assertions: 验证结果是否符合预期 (和之前完全一样)
    assert isinstance(df, pd.DataFrame), "The result should be a pandas DataFrame."
    assert not df.empty, "The DataFrame should not be empty."

    # 验证总行数：2 CPUs * 2 timestamps * 3 events = 12 rows
    assert df.shape[0] == 12, f"Expected 12 rows, but got {df.shape[0]}."

    # 验证核心列是否存在
    expected_columns = {"timestamp", "cpu_id", "value", "metric_type"}
    assert expected_columns.issubset(
        df.columns
    ), f"DataFrame is missing one of the core columns: {expected_columns}."

    # 验证数据类型
    assert df["timestamp"].dtype == "float64"
    assert df["cpu_id"].dtype == "int64"  # 注意：astype('int') 之后可能是 int64
    assert df["value"].dtype == "Int64"  # 可空整数

    # 验证一个具体的值
    instr_cpu1_t1 = df[
        (df["timestamp"] == 1.0)
        & (df["cpu_id"] == 1)
        & (df["metric_type"] == "instructions:D")
    ]
    assert instr_cpu1_t1["value"].iloc[0] == 800, "The parsed value is incorrect."


# 聚合模式的测试数据字符串
AGGREGATED_PERF_STAT_DATA = """
# Test data for aggregated perf stat format
1.000,2200,,cycles:D,1000,100.00,,
1.000,1300,,instructions:D,1000,100.00,0.59,insn per cycle
2.000,2400,,cycles:D,1000,100.00,,
2.000,1430,,instructions:D,1000,100.00,0.60,insn per cycle
"""


def test_parse_perf_stat_file_with_aggregated_format():
    """
    Tests if the parser can correctly handle aggregated mode output,
    which lacks a cpu_id column.
    """
    # 1. Action
    string_io_buffer = io.StringIO(AGGREGATED_PERF_STAT_DATA)
    df = PerfStatParser.parse_perf_stat_file(string_io_buffer)

    # 2. Assertions
    assert not df.empty, "DataFrame should not be empty for aggregated data."
    assert df.shape[0] == 4, f"Expected 4 rows, but got {df.shape[0]}."

    # 关键断言: 检查 cpu_id 是否都被正确地设置为了 -1
    assert "cpu_id" in df.columns, "cpu_id column should be added."
    assert (
        df["cpu_id"] == -1
    ).all(), "All cpu_id values should be -1 in aggregated mode."

    # 验证一个具体的值
    cycles_t1 = df[(df["timestamp"] == 1.0) & (df["metric_type"] == "cycles:D")]
    assert (
        cycles_t1["value"].iloc[0] == 2200
    ), "The parsed aggregated value is incorrect."


class TestPerfStatDataProcessor:

    # pytest 的 setup 方法，会在每个测试函数运行前都执行一次
    # 这让我们可以在所有测试中复用同一个 data processor 对象
    def setup_method(self):
        # 使用我们已经验证过的 modern format 数据
        string_io_buffer = io.StringIO(MODERN_PERF_STAT_DATA)
        # 注意：我们直接用 PerfStatData 来创建对象，因为它会自动处理所有事情
        self.perf_stat_data = PerfStatData(string_io_buffer)
        self.processor = (
            self.perf_stat_data.data_processor
        )  # PerfStatDataProcessor 对象

    def test_get_events_overall_system(self):
        """Tests calculating the system-wide total for an event."""
        # cycles 的总和应该是 1000 + 1200 + 1100 + 1300 = 4600
        total_cycles = self.processor.get_events_overall("cycles", data_type="system")
        assert total_cycles == 4600

    def test_get_events_overall_thread(self):
        """Tests calculating the per-thread total for an event."""
        per_thread_cycles = self.processor.get_events_overall(
            "cycles", data_type="thread"
        )
        assert isinstance(per_thread_cycles, pd.DataFrame)
        # CPU0 的 cycles 总和应该是 1000 + 1100 = 2100
        assert per_thread_cycles.iloc[0]["value"] == 2100
        # CPU1 的 cycles 总和应该是 1200 + 1300 = 2500
        assert per_thread_cycles.iloc[1]["value"] == 2500

    def test_get_cpi(self):
        """Tests the get_CPI calculation."""
        # 这个方法现在应该能跑通了
        cpi_df = self.processor.get_CPI()
        assert not cpi_df.empty
        assert "CPI" in cpi_df.columns
        # 我们可以验证一个具体的 CPI 值
        # 对于 CPU0 在 timestamp=1.0 时, CPI = cycles/instructions = 1000/500 = 2.0
        cpi_cpu0_t1 = cpi_df[(cpi_df["timestamp"] == 1.0) & (cpi_df["cpu_id"] == 0)]
        assert cpi_cpu0_t1["CPI"].iloc[0] == 2.0

    def test_get_cpi_time_system_average(self):
        """
        Tests get_CPI_time with threads=None to get the system average.
        """

        # 1. Action
        # self.processor 是我们在 setup_method 里创建好的
        system_avg_cpi_df = self.processor.get_CPI_time(threads=None)

        # 2. Assertions
        assert isinstance(system_avg_cpi_df, pd.DataFrame)
        assert not system_avg_cpi_df.empty
        assert "CPI" in system_avg_cpi_df.columns

        # 索引应该是 timestamp
        assert system_avg_cpi_df.index.name == "timestamp"

    def test_get_cpi_time_for_specific_threads(self):
        """
        Tests get_CPI_time for a specific list of threads.
        """
        # 1. Action
        specific_threads = [0, 1]
        cpi_df = self.processor.get_CPI_time(threads=specific_threads)

        # 2. Assertions
        assert isinstance(cpi_df, pd.DataFrame)
        assert not cpi_df.empty
        # 检查返回的 DataFrame 是否只包含了我们指定的 CPU
        assert set(cpi_df["cpu_id"].unique()) == set(specific_threads)

    # 在 TestPerfStatDataProcessor 类里增加

    def test_get_cpi_overall_by_thread(self):
        """Tests get_CPI_overall with data_type='thread'."""
        # 1. Action
        # self.processor 是我们在 setup_method 里创建好的
        cpi_per_thread_df = self.processor.get_CPI_overall(data_type="thread")

        # 2. Assertions
        assert isinstance(cpi_per_thread_df, pd.DataFrame)
        assert not cpi_per_thread_df.empty
        assert "CPI" in cpi_per_thread_df.columns
        assert cpi_per_thread_df.index.name == "cpu_id"

        # 验证 CPU0 的数据
        # 根据 MODERN_PERF_STAT_DATA:
        # CPU0 cycles = 1000 + 1100 = 2100
        # CPU0 instructions = 500 + 550 = 1050
        # CPU0 CPI = 2100 / 1050 = 2.0
        cpu0_data = cpi_per_thread_df.loc[0]
        assert cpu0_data.at["value_cycles"] == 2100
        assert cpu0_data.at["value_instructions"] == 1050
        assert cpu0_data.at["CPI"] == 2.0

    def test_get_cpi_overall_system(self):
        """Tests get_CPI_overall with data_type='system'."""
        # 1. Action
        system_cpi = self.processor.get_CPI_overall(data_type="system")

        # 2. Assertions
        # 根据 MODERN_PERF_STAT_DATA:
        # total_cycles = (1000+1200) + (1100+1300) = 4600
        # total_instructions = (500+800) + (550+880) = 2730
        # system_cpi = 4600 / 2730
        expected_cpi = (1000 + 1200 + 1100 + 1300) / (500 + 800 + 550 + 880)

        # 使用 pytest.approx 来处理浮点数比较
        assert system_cpi == pytest.approx(expected_cpi)

    def test_get_cpi_overall_invalid_type(self):
        """Tests that get_CPI_overall raises ValueError for invalid data_type."""
        # pytest.raises 是一个上下文管理器，用来检查异常
        with pytest.raises(ValueError, match="Invalid data type"):
            self.processor.get_CPI_overall(data_type="invalid_type")


def test_parse_non_existent_file():
    """
    Tests that the parser returns an empty DataFrame when the file does not exist.
    """
    # 1. Action: 传入一个肯定不存在的路径
    df = PerfStatParser.parse_perf_stat_file("/dev/null/you_wont_find_me.csv")

    # 2. Assertions
    assert isinstance(df, pd.DataFrame)
    assert df.empty, "Should return an empty DataFrame for a non-existent file."


def test_parse_empty_file():
    """
    Tests that the parser returns an empty DataFrame for an empty or commented file.
    """
    EMPTY_DATA = "# This file is empty or only has comments"
    string_io_buffer = io.StringIO(EMPTY_DATA)
    df = PerfStatParser.parse_perf_stat_file(string_io_buffer)

    assert isinstance(df, pd.DataFrame)
    assert df.empty, "Should return an empty DataFrame for an empty file."


def test_parse_malformed_file_without_event_name():
    """
    Tests handling of a malformed CSV that lacks a recognizable event name column.
    """
    MALFORMED_DATA = """
    1.000,CPU0,1000,,no_event_here
    """
    string_io_buffer = io.StringIO(MALFORMED_DATA)
    df = PerfStatParser.parse_perf_stat_file(string_io_buffer)

    assert isinstance(df, pd.DataFrame)
    assert df.empty, "Should return an empty DataFrame for malformed data."


def test_parse_csv_with_only_nan_values():
    """
    Tests that the parser returns an empty DataFrame when CSV contains only NaN values.
    This will trigger the df.empty check at line 59 after successful pd.read_csv but
    subsequent data cleaning removes all rows with NaN values.
    """
    # 这种数据会被pd.read_csv成功读取，但value列全是NaN，在后续处理中被清除
    NAN_ONLY_DATA = ",,,\n,,,\n"
    string_io_buffer = io.StringIO(NAN_ONLY_DATA)
    df = PerfStatParser.parse_perf_stat_file(string_io_buffer)

    assert isinstance(df, pd.DataFrame)
    assert df.empty, "Should return an empty DataFrame when all values are NaN."
