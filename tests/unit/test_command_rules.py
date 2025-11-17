import pandas as pd
import pytest

# 核心修改: 我们现在只测试 run_rules_engine, 并且从新的 report 模块导入 context builder
from src.pipa.commands.rules import load_rules, run_rules_engine
from src.pipa.report.context_builder import build_full_context
from src.utils import get_project_root

# --- Fixtures for ON-CPU (TMA) Testing ---


@pytest.fixture
def mock_tma_dataframes():
    """提供一个模拟 ON-CPU 场景的数据字典，包含 TMA 计算所需的 perf 事件。"""
    return {
        "perf_raw": pd.DataFrame(
            {
                "cpu": ["all"] * 5,
                "event_name": ["instructions", "cycles", "stalled-cycles-frontend", "branch-misses", "LLC-load-misses"],
                "value": [
                    1_000_000_000,
                    2_000_000_000,
                    600_000_000,
                    50_000_000,
                    30_000_000,
                ],
            }
        ),
        "sar_cpu": pd.DataFrame({"CPU": ["all"], "%user": [90.0], "%system": [5.0]}),
    }


# --- Fixtures for OFF-CPU Testing ---


@pytest.fixture
def mock_off_cpu_io_dataframes():
    """提供一个模拟 OFF-CPU 磁盘瓶颈场景的数据字典。"""
    return {
        "sar_io": pd.DataFrame({"%util": [85.0], "await": [30.0], "avgrq-sz": [8.0], "avgqu-sz": [10.0]}),
        "sar_cpu": pd.DataFrame({"CPU": ["all"], "%user": [10.0], "%system": [5.0], "%iowait": [20.0]}),
    }


@pytest.fixture
def mock_static_info():
    """提供一个包含 CPU 核心数的 mock static_info 字典。"""
    return {"cpu_info": {"CPU(s)": 8}}


@pytest.fixture
def full_decision_tree():
    """加载真实的决策树以供测试。"""
    rules_path = get_project_root() / "config/rules/decision_tree.yaml"
    rules, config = load_rules(rules_path)
    return rules, config


# --- Test Cases for the New World ---


def test_on_cpu_tma_frontend_bound_path(mock_static_info, full_decision_tree):
    """
    测试 TMA L1 前端瓶颈的诊断路径。
    我们通过**显著提高** stalled-cycles-frontend 的值来精确触发此路径。
    """
    rules, config = full_decision_tree

    mock_dataframes = {
        "perf_raw": pd.DataFrame(
            {
                "cpu": ["all"] * 4,
                "event_name": ["instructions", "cycles", "stalled-cycles-frontend", "branch-misses"],
                "value": [
                    1_000_000_000,
                    4_000_000_000,
                    3_300_000_000,
                    10_000_000,
                ],
            }
        ),
        "sar_cpu": pd.DataFrame({"CPU": ["all"], "%user": [90.0], "%system": [5.0]}),
    }

    context = build_full_context(mock_dataframes, mock_static_info)
    context.update(config)

    findings = run_rules_engine(mock_dataframes, rules, context)

    findings_text = "".join(findings)
    assert "ON-CPU" in findings_text
    assert "前端瓶颈" in findings_text, f"诊断结论: {findings_text}"
    assert "CPU 大部分时间在“饥饿”状态" in findings_text


def test_on_cpu_tma_backend_bound_path(mock_static_info, full_decision_tree):
    """
    测试 TMA L1 后端瓶颈的诊断路径。
    我们使用一个更接近真实世界的、IPC 较低且前端停顿不占主导的数据集。
    """
    rules, config = full_decision_tree

    mock_dataframes = {
        "perf_raw": pd.DataFrame(
            {
                "cpu": ["all"] * 4,
                "event_name": ["instructions", "cycles", "stalled-cycles-frontend", "branch-misses"],
                "value": [
                    1_000_000_000,
                    2_000_000_000,
                    100_000_000,
                    5_000_000,
                ],
            }
        ),
        "sar_cpu": pd.DataFrame({"CPU": ["all"], "%user": [90.0], "%system": [5.0]}),
    }

    context = build_full_context(mock_dataframes, mock_static_info)
    context.update(config)

    findings = run_rules_engine(mock_dataframes, rules, context)

    findings_text = "".join(findings)
    assert "ON-CPU" in findings_text
    assert "后端瓶颈" in findings_text
    assert "CPU 执行单元“停滞”" in findings_text


def test_off_cpu_disk_io_path(mock_off_cpu_io_dataframes, mock_static_info, full_decision_tree):
    """测试 OFF-CPU 磁盘 I/O 瓶颈的全路径诊断。"""
    rules, config = full_decision_tree

    context = build_full_context(mock_off_cpu_io_dataframes, mock_static_info)
    context.update(config)

    findings = run_rules_engine(mock_off_cpu_io_dataframes, rules, context)

    findings_text = "".join(findings)
    assert "OFF-CPU" in findings_text
    assert "磁盘 I/O 瓶颈" in findings_text
    assert "吞吐量饱和" in findings_text
    assert "高延迟" in findings_text
    assert "随机 I/O 密集" in findings_text
