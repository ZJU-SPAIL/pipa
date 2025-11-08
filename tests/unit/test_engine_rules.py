import pandas as pd
import pytest

from src.engine.rules import calculate_context_metrics, run_rules_engine

# --- Mocks and Fixtures ---


@pytest.fixture
def mock_static_info():
    """提供一个包含 CPU 核心数的 mock static_info 字典。"""
    return {"cpu_info": {"CPUs_Count": 16}}


@pytest.fixture
def mock_v2_rules():
    """提供一个层次化的 V2 mock 规则，现在包含对 num_cpu 的检查。"""
    return [
        {
            "name": "PIPA Root",
            "precondition": "True",
            "sub_rules": [
                {
                    "name": "ON-CPU Branch",
                    "precondition": "'total_cpu' in locals() and total_cpu > 75",
                    "finding": "诊断：**ON-CPU** (利用率 **{total_cpu:.2f}%**)。",
                },
                {
                    "name": "OFF-CPU Branch",
                    "precondition": "'total_cpu' in locals() and total_cpu <= 75",
                    "finding": "诊断：**OFF-CPU**。",
                    "sub_rules": [
                        {
                            "name": "High System Load",
                            "precondition": (
                                "'load_queue' in df and 'ldavg-1' in df['load_queue'] and 'num_cpu' in locals() and "
                                "num_cpu > 0 and df['load_queue']['ldavg-1'].mean() / num_cpu > 0.8"
                            ),
                            "finding": "根因：**系统负载过高** (1分钟平均负载 **{avg_load1:.2f}**，是CPU核心数的 **{load_ratio:.1f}x**)。",
                        }
                    ],
                },
            ],
        }
    ]


# --- Test Cases ---


def test_calculate_context_metrics_extracts_num_cpu(mock_static_info):
    """测试 calculate_context_metrics 能否从 static_info 中正确提取 num_cpu。"""
    context = calculate_context_metrics({}, mock_static_info)
    assert "num_cpu" in context
    assert context["num_cpu"] == 16


def test_calculate_context_metrics_handles_missing_cpu_info():
    """测试在 static_info 或 cpu_info 缺失时，函数能优雅地处理。"""
    context_empty = calculate_context_metrics({}, {})
    assert "num_cpu" not in context_empty

    context_no_cpu_info = calculate_context_metrics({}, {"other_info": {}})
    assert "num_cpu" not in context_no_cpu_info


def test_run_rules_engine_with_dynamic_cpu_context(mock_v2_rules, mock_static_info):
    """
    核心测试：验证规则引擎现在可以使用动态注入的 num_cpu 上下文来做出正确判断。
    """
    mock_dataframes_low_load = {
        "cpu": pd.DataFrame({"pct_usr": [20.0], "pct_sys": [10.0]}),
        "load_queue": pd.DataFrame({"ldavg-1": [15.0]}),
    }
    context_low = calculate_context_metrics(mock_dataframes_low_load, mock_static_info)
    findings_low = run_rules_engine(mock_dataframes_low_load, mock_v2_rules, context_low)
    assert "诊断：**OFF-CPU**。" in findings_low
    assert "根因：**系统负载过高**" not in findings_low

    mock_dataframes_high_load = {
        "cpu": pd.DataFrame({"pct_usr": [20.0], "pct_sys": [10.0]}),
        "load_queue": pd.DataFrame({"ldavg-1": [20.0]}),
    }
    context_high = calculate_context_metrics(mock_dataframes_high_load, mock_static_info)
    context_high["load_ratio"] = context_high["avg_load1"] / context_high["num_cpu"]
    findings_high = run_rules_engine(mock_dataframes_high_load, mock_v2_rules, context_high)
    assert "根因：**系统负载过高**" in "".join(findings_high)
