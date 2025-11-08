import pandas as pd
import pytest

from src.engine.rules import calculate_context_metrics, run_rules_engine


def test_calculate_context_metrics_all_data_present():
    """
    测试当所有必需的 DataFrame 都存在且包含有效数据时，
    calculate_context_metrics 函数能否正确计算所有衍生指标。
    """
    mock_dataframes = {
        "cpu": pd.DataFrame({"pct_usr": [10.0, 20.0], "pct_sys": [5.0, 10.0]}),
        "proc_cswch": pd.DataFrame({"cswch_per_s": [1000, 3000]}),
        "device_io": pd.DataFrame({"tps": [50.0, 150.0]}),
        "paging": pd.DataFrame({"pswpin_per_s": [2.0, 8.0], "pswpout_per_s": [3.0, 7.0]}),
        "load_queue": pd.DataFrame({"ldavg-1": [1.5, 2.5]}),
    }

    context = calculate_context_metrics(mock_dataframes)

    assert isinstance(context, dict)
    assert "total_cpu" in context
    assert context["total_cpu"] == pytest.approx(22.5)
    assert "avg_cswch" in context
    assert context["avg_cswch"] == pytest.approx(2000.0)
    assert "total_tps" in context
    assert context["total_tps"] == pytest.approx(200.0)
    assert "avg_swaps" in context
    assert context["avg_swaps"] == pytest.approx(10.0)
    assert "avg_load1" in context
    assert context["avg_load1"] == pytest.approx(2.0)


def test_calculate_context_metrics_missing_and_empty_data():
    """
    测试当部分 DataFrame 缺失或为空时，函数能否健壮地处理，
    只计算可用的指标，且不引发错误。
    """
    mock_dataframes = {
        "cpu": pd.DataFrame({"pct_usr": [10.0, 30.0], "pct_sys": [0.0, 0.0]}),
        "device_io": pd.DataFrame(),
        "paging": pd.DataFrame({"pswpin_per_s": [5.0], "pswpout_per_s": [5.0]}),
    }

    context = calculate_context_metrics(mock_dataframes)

    assert isinstance(context, dict)

    assert "total_cpu" in context
    assert context["total_cpu"] == pytest.approx(20.0)
    assert "avg_swaps" in context
    assert context["avg_swaps"] == pytest.approx(10.0)

    assert "avg_cswch" not in context
    assert "total_tps" not in context
    assert "avg_load1" not in context


@pytest.fixture
def mock_rules_config():
    """提供一个简化的、层次化的 mock 规则配置，用于测试规则引擎的逻辑。"""
    return [
        {
            "name": "Root",
            "precondition": "True",
            "sub_rules": [
                {
                    "name": "ON-CPU Branch",
                    "precondition": "'total_cpu' in locals() and total_cpu > 75",
                    "finding": "ON-CPU: High utilization detected ({total_cpu:.2f}%).",
                    "sub_rules": [
                        {
                            "name": "High Context Switching",
                            "precondition": "'proc_cswch' in df and df['proc_cswch']['cswch_per_s'].mean() > 10000",
                            "finding": "ON-CPU Sub-Rule: Context switching is high.",
                        }
                    ],
                },
                {
                    "name": "OFF-CPU Branch",
                    "precondition": "'total_cpu' in locals() and total_cpu <= 75",
                    "finding": "OFF-CPU: Low utilization detected ({total_cpu:.2f}%).",
                    "sub_rules": [
                        {
                            "name": "Frequent Swapping",
                            "precondition": "'avg_swaps' in locals() and avg_swaps > 10",
                            "finding": "OFF-CPU Sub-Rule: System is swapping.",
                        }
                    ],
                },
            ],
        }
    ]


def test_run_rules_engine_triggers_on_cpu_path(mock_rules_config):
    """
    测试当数据指示高 CPU 利用率时，规则引擎能否正确匹配并返回 ON-CPU 路径的 findings。
    """
    mock_dataframes = {
        "cpu": pd.DataFrame({"pct_usr": [80.0], "pct_sys": [10.0]}),
        "proc_cswch": pd.DataFrame({"cswch_per_s": [20000]}),
        "paging": pd.DataFrame({"pswpin_per_s": [0], "pswpout_per_s": [0]}),
    }
    context = calculate_context_metrics(mock_dataframes)

    findings = run_rules_engine(mock_dataframes, mock_rules_config, context)

    assert len(findings) == 2
    assert "ON-CPU: High utilization detected (90.00%)." in findings
    assert "ON-CPU Sub-Rule: Context switching is high." in findings
    assert not any("OFF-CPU" in f for f in findings)


def test_run_rules_engine_triggers_off_cpu_path(mock_rules_config):
    """
    测试当数据指示低 CPU 利用率和高 swapping 时，规则引擎能否正确匹配 OFF-CPU 路径。
    """
    mock_dataframes = {
        "cpu": pd.DataFrame({"pct_usr": [20.0], "pct_sys": [5.0]}),
        "paging": pd.DataFrame({"pswpin_per_s": [50.0], "pswpout_per_s": [50.0]}),
    }
    context = calculate_context_metrics(mock_dataframes)

    findings = run_rules_engine(mock_dataframes, mock_rules_config, context)

    assert len(findings) == 2
    assert "OFF-CPU: Low utilization detected (25.00%)." in findings
    assert "OFF-CPU Sub-Rule: System is swapping." in findings
    assert not any("ON-CPU" in f for f in findings)


def test_run_rules_engine_no_findings_for_healthy_system(mock_rules_config):
    """
    测试对于“健康”的系统数据（不触发任何特定瓶颈），规则引擎不返回任何 finding。
    """
    mock_dataframes = {
        "cpu": pd.DataFrame({"pct_usr": [40.0], "pct_sys": [10.0]}),
        "proc_cswch": pd.DataFrame({"cswch_per_s": [5000]}),
        "paging": pd.DataFrame({"pswpin_per_s": [0], "pswpout_per_s": [0]}),
    }
    context = calculate_context_metrics(mock_dataframes)

    findings = run_rules_engine(mock_dataframes, mock_rules_config, context)

    assert len(findings) == 1
    assert "OFF-CPU: Low utilization detected (50.00%)." in findings
    assert not any("Sub-Rule" in f for f in findings)
