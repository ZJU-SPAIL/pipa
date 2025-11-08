import pandas as pd
import pytest

from src.engine.rules import calculate_context_metrics, run_rules_engine


# calculate_context_metrics 的测试保持不变，因为其逻辑没有改变
def test_calculate_context_metrics_all_data_present():
    """测试当所有必需的 DataFrame 都存在时，函数能正确计算所有衍生指标。"""
    mock_dataframes = {
        "cpu": pd.DataFrame({"pct_usr": [10.0, 20.0], "pct_sys": [5.0, 10.0]}),
        "proc_cswch": pd.DataFrame({"cswch_per_s": [1000, 3000]}),
        "device_io": pd.DataFrame({"tps": [50.0, 150.0]}),
        "paging": pd.DataFrame({"pswpin_per_s": [2.0, 8.0], "pswpout_per_s": [3.0, 7.0]}),
        "load_queue": pd.DataFrame({"ldavg-1": [1.5, 2.5]}),
    }
    context = calculate_context_metrics(mock_dataframes)
    assert context["total_cpu"] == pytest.approx(22.5)
    assert context["avg_cswch"] == pytest.approx(2000.0)


def test_calculate_context_metrics_missing_and_empty_data():
    """测试当部分 DataFrame 缺失或为空时，函数能健壮地处理。"""
    mock_dataframes = {
        "cpu": pd.DataFrame({"pct_usr": [10.0, 30.0], "pct_sys": [0.0, 0.0]}),
        "device_io": pd.DataFrame(),
    }
    context = calculate_context_metrics(mock_dataframes)
    assert "total_cpu" in context
    assert context["total_cpu"] == pytest.approx(20.0)
    assert "avg_cswch" not in context
    assert "total_tps" not in context


# --- V2 规则引擎的全新测试套件 ---


@pytest.fixture
def mock_v2_rules():
    """提供一个层次化的 V2 mock 规则，其 precondition 已修正为直接访问 context 变量。"""
    return [
        {
            "name": "PIPA Root",
            "precondition": "True",
            "sub_rules": [
                {
                    "name": "ON-CPU Branch",
                    "precondition": "'total_cpu' in locals() and total_cpu > 75",
                    "finding": "诊断：ON-CPU (利用率 {total_cpu:.2f}%)。",
                    "sub_rules": [
                        {
                            "name": "High Context Switches",
                            "precondition": "'avg_cswch' in locals() and avg_cswch > 100000",
                            "finding": "根因：高上下文切换。",
                        },
                        {
                            "name": "Frontend Bound (Future)",
                            "precondition": "'tma' in df and df['tma']['Frontend_Bound'].mean() > 0.2",
                            "finding": "根因：前端受限。",
                        },
                    ],
                },
                {
                    "name": "OFF-CPU Branch",
                    "precondition": "'total_cpu' in locals() and total_cpu <= 75",
                    "finding": "诊断：OFF-CPU。",
                },
            ],
        }
    ]


def test_run_rules_engine_v2_deep_path_triggered(mock_v2_rules):
    """测试 V2 引擎：验证当数据满足深层条件时，递归逻辑能正确触发所有层级的 finding。"""
    mock_dataframes = {
        "cpu": pd.DataFrame({"pct_usr": [80.0], "pct_sys": [10.0]}),
        "proc_cswch": pd.DataFrame({"cswch_per_s": [200000]}),
    }
    context = calculate_context_metrics(mock_dataframes)
    findings = run_rules_engine(mock_dataframes, mock_v2_rules, context)

    assert len(findings) == 2
    assert "诊断：ON-CPU (利用率 90.00%)。" in findings
    assert "根因：高上下文切换。" in findings


def test_run_rules_engine_v2_branch_pruning(mock_v2_rules):
    """测试 V2 引擎：验证当父节点条件不满足时，其所有子节点都被“剪枝”，不被评估。"""
    mock_dataframes = {
        "cpu": pd.DataFrame({"pct_usr": [80.0], "pct_sys": [10.0]}),
        "proc_cswch": pd.DataFrame({"cswch_per_s": [5000]}),
    }
    context = calculate_context_metrics(mock_dataframes)
    findings = run_rules_engine(mock_dataframes, mock_v2_rules, context)

    assert len(findings) == 1
    assert "诊断：ON-CPU (利用率 90.00%)。" in findings
    assert "根因：高上下文切换。" not in findings


def test_run_rules_engine_v2_handles_missing_data_gracefully(mock_v2_rules):
    """测试 V2 引擎：验证当规则所需的数据（如 'tma'）不存在时，引擎不会崩溃，而是优雅跳过。"""
    mock_dataframes = {
        "cpu": pd.DataFrame({"pct_usr": [90.0], "pct_sys": [0.0]}),
    }
    context = calculate_context_metrics(mock_dataframes)
    findings = run_rules_engine(mock_dataframes, mock_v2_rules, context)

    assert len(findings) == 1
    assert "诊断：ON-CPU (利用率 90.00%)。" in findings
    assert "根因：前端受限。" not in findings
