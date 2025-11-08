import logging
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from src.commands.sample import sample
from src.parsers.perf_stat_timeseries_parser import parse_perf_stat_timeseries
from src.parsers.sar_timeseries_parser import parse_sar_timeseries

# 将此文件中的所有测试标记为 'integration'
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def live_sample_output_dir(tmp_path_factory) -> Path:
    """
    一个健壮的 fixture，通过将日志重定向到文件来解决 pytest 和 CliRunner
    之间的 I/O 冲突。它运行一次 `pipa sample` 来生成真实的采集器输出。
    """
    base_temp_dir = tmp_path_factory.mktemp("integration_assets")
    pipa_archive_path = base_temp_dir / "integration_run.pipa"
    log_file_path = base_temp_dir / "pipa_sample_integration.log"
    unpacked_dir = base_temp_dir / "unpacked"
    unpacked_dir.mkdir()

    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]

    try:
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        root_logger.handlers.clear()
        root_logger.addHandler(file_handler)
        root_logger.setLevel(logging.INFO)

        runner = CliRunner()
        result = runner.invoke(
            sample,
            [
                "--workload",
                "stress_cpu",
                "--intensity",
                "1",
                "--duration",
                "2",
                "--output",
                str(pipa_archive_path),
            ],
            catch_exceptions=False,
        )

    finally:
        root_logger.handlers = original_handlers
        print(f"\n--- Captured log from {log_file_path.name} ---")
        print(log_file_path.read_text())
        print("--- End of captured log ---")

    assert result.exit_code == 0, f"pipa sample 命令失败: {result.output}"
    assert pipa_archive_path.exists(), ".pipa 归档文件未被创建。"

    shutil.unpack_archive(pipa_archive_path, unpacked_dir, format="gztar")

    level_dir = next((d for d in unpacked_dir.iterdir() if d.is_dir()), None)
    assert level_dir, "在解压的归档中未找到任何层级目录。"

    return level_dir


def test_perf_parser_with_live_data(live_sample_output_dir):
    perf_file = live_sample_output_dir / "perf_stat.txt"
    assert perf_file.exists(), "perf_stat.txt 未被 sample 命令生成。"

    content = perf_file.read_text()
    assert content, "perf_stat.txt 为空。"

    df = parse_perf_stat_timeseries(content)

    assert not df.empty, "解析实时的 perf_stat.txt 得到了一个空的 DataFrame。"
    assert "timestamp" in df.columns
    assert "event_name" in df.columns
    assert "value" in df.columns


def test_sar_parser_with_live_data(live_sample_output_dir):
    sar_file = live_sample_output_dir / "sar_cpu.txt"
    assert sar_file.exists(), "sar_cpu.txt 未被 sample 命令生成。"

    content = sar_file.read_text()
    assert content, "sar_cpu.txt 为空。"

    results = parse_sar_timeseries(content)

    assert results, "解析实时的 sar_cpu.txt 得到了一个空字典。"
    assert "cpu" in results, "从实时的 sar 数据中未能解析出 'cpu' 块。"
    assert not results["cpu"].empty, "解析后 'cpu' DataFrame 为空。"
