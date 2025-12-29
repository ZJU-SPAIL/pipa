import pandas as pd
import pytest
from markdown_it import MarkdownIt

from pipa.commands.rules import format_rules_to_html_tree, load_rules
from pipa.report.context_builder import build_full_context
from pipa.utils import get_project_root


@pytest.fixture
def mock_off_cpu_io_dataframes():
    """提供一个模拟 OFF-CPU 磁盘瓶颈场景的数据字典。"""

    return {
        "sar_io": pd.DataFrame(
            {"%util": [85.0], "await": [30.0], "avgrq-sz": [8.0], "avgqu-sz": [85.0]}
        ),
        "sar_disk": pd.DataFrame(
            {
                "DEV": ["sda"],
                "%util": [85.0],
                "await": [30.0],
                "avgrq-sz": [8.0],
                "avgqu-sz": [85.0],
            }
        ),
        "sar_cpu": pd.DataFrame(
            {
                "CPU": ["all", "0", "1", "2", "3", "4", "5", "6", "7"],
                "%user": [10.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0],
                "%system": [5.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0],
                "%iowait": [20.0, 25.0, 20.0, 15.0, 10.0, 5.0, 5.0, 5.0, 5.0],
                "%idle": [65.0, 68.0, 73.0, 78.0, 83.0, 88.0, 88.0, 88.0, 88.0],
            }
        ),
    }


@pytest.fixture
def mock_static_info():
    """提供一个包含 CPU 核心数的 mock static_info 字典。"""

    return {"cpu_info": {"CPU(s)": 8}}


@pytest.fixture
def full_decision_tree():
    """加载真实的决策树以供测试。"""

    rules_path = get_project_root() / "config" / "rules" / "decision_tree.yaml"
    rules, config = load_rules(rules_path)
    return rules, config


def test_off_cpu_disk_io_path(
    mock_off_cpu_io_dataframes, mock_static_info, full_decision_tree
):
    """测试 OFF-CPU 磁盘 I/O 瓶颈的全路径诊断。"""

    rules, config = full_decision_tree
    mock_static_info["disk_info"] = {
        "block_devices": [{"name": "sda", "rotational": "SSD"}]
    }

    context = build_full_context(mock_off_cpu_io_dataframes, mock_static_info)
    config.update(
        {
            "IO_AWAIT_SATA_SSD_THRESHOLD": 20.0,
            "IO_AWAIT_NVME_SSD_THRESHOLD": 5.0,
            "IO_AWAIT_HDD_THRESHOLD": 50.0,
        }
    )
    context.update(config)

    md = MarkdownIt()
    _, _, findings_html = format_rules_to_html_tree(
        rules, mock_off_cpu_io_dataframes, context, md
    )
    findings_text = "".join([findings_html])

    assert "OFF-CPU" in findings_text
    assert "磁盘 I/O" in findings_text


def test_effective_await_threshold_hdd(mock_static_info, full_decision_tree):
    """验证 HDD 子类型阈值选择与上下文注入。"""

    _, config = full_decision_tree

    mock_dataframes = {
        "sar_disk": pd.DataFrame(
            {
                "DEV": ["sda"],
                "%util": [50.0],
                "await": [35.0],
                "avgrq-sz": [8.0],
                "avgqu-sz": [20.0],
            }
        ),
        "sar_cpu": pd.DataFrame(
            {
                "CPU": ["all", "0", "1", "2", "3"],
                "%user": [5.0, 5.0, 5.0, 5.0, 5.0],
                "%system": [2.0, 2.0, 2.0, 2.0, 2.0],
                "%iowait": [15.0, 15.0, 15.0, 15.0, 15.0],
                "%idle": [78.0, 78.0, 78.0, 78.0, 78.0],
            }
        ),
    }
    mock_static_info["disk_info"] = {
        "block_devices": [{"name": "sda", "rotational": "HDD"}]
    }

    context = build_full_context(mock_dataframes, mock_static_info, rule_configs=config)

    assert context.get("busiest_disk_subtype") == "HDD"
    assert context.get("effective_await_threshold") == config.get(
        "IO_AWAIT_HDD_THRESHOLD"
    )


def test_effective_await_threshold_nvme(mock_static_info, full_decision_tree):
    """验证 NVME SSD 子类型阈值选择与上下文注入。"""

    _, config = full_decision_tree

    mock_dataframes = {
        "sar_disk": pd.DataFrame(
            {
                "DEV": ["nvme0n1"],
                "%util": [50.0],
                "await": [2.5],
                "avgrq-sz": [8.0],
                "avgqu-sz": [5.0],
            }
        ),
        "sar_cpu": pd.DataFrame(
            {
                "CPU": ["all", "0", "1", "2", "3"],
                "%user": [5.0, 5.0, 5.0, 5.0, 5.0],
                "%system": [2.0, 2.0, 2.0, 2.0, 2.0],
                "%iowait": [1.0, 1.0, 1.0, 1.0, 1.0],
                "%idle": [92.0, 92.0, 92.0, 92.0, 92.0],
            }
        ),
    }
    mock_static_info["disk_info"] = {
        "block_devices": [{"name": "nvme0n1", "rotational": "SSD"}]
    }

    context = build_full_context(mock_dataframes, mock_static_info, rule_configs=config)

    assert context.get("busiest_disk_subtype") == "NVME_SSD"
    assert context.get("effective_await_threshold") == config.get(
        "IO_AWAIT_NVME_SSD_THRESHOLD"
    )


def test_effective_await_threshold_sata(mock_static_info, full_decision_tree):
    """验证 SATA SSD 子类型阈值选择与上下文注入。"""

    _, config = full_decision_tree

    mock_dataframes = {
        "sar_disk": pd.DataFrame(
            {
                "DEV": ["sda"],
                "%util": [50.0],
                "await": [6.0],
                "avgrq-sz": [8.0],
                "avgqu-sz": [5.0],
            }
        ),
        "sar_cpu": pd.DataFrame(
            {
                "CPU": ["all", "0", "1", "2", "3"],
                "%user": [5.0, 5.0, 5.0, 5.0, 5.0],
                "%system": [2.0, 2.0, 2.0, 2.0, 2.0],
                "%iowait": [1.0, 1.0, 1.0, 1.0, 1.0],
                "%idle": [92.0, 92.0, 92.0, 92.0, 92.0],
            }
        ),
    }
    mock_static_info["disk_info"] = {
        "block_devices": [{"name": "sda", "rotational": "SSD"}]
    }

    context = build_full_context(mock_dataframes, mock_static_info, rule_configs=config)

    assert context.get("busiest_disk_subtype") == "SATA_SSD"
    assert context.get("effective_await_threshold") == config.get(
        "IO_AWAIT_SATA_SSD_THRESHOLD"
    )
