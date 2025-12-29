import pandas as pd

from pipa.report.cluster_analyzer import analyze_cpu_clusters


def test_analyze_cpu_clusters_empty():
    assert analyze_cpu_clusters(pd.DataFrame()) == {}


def test_analyze_cpu_clusters_insufficient_cores():
    df = pd.DataFrame(
        {
            "CPU": ["0", "all"],
            "%user": [1.0, 2.0],
            "%system": [1.0, 2.0],
            "%iowait": [0.0, 0.0],
            "%idle": [98.0, 96.0],
        }
    )
    assert analyze_cpu_clusters(df) == {}


def test_analyze_cpu_clusters_basic_grouping():
    df = pd.DataFrame(
        {
            "CPU": ["0", "1", "2", "3"],
            "%user": [1.0, 20.0, 5.0, 50.0],
            "%system": [1.0, 5.0, 3.0, 10.0],
            "%iowait": [0.0, 0.0, 0.0, 0.0],
            "%idle": [98.0, 75.0, 92.0, 40.0],
        }
    )

    res = analyze_cpu_clusters(
        df, {"CPU_CLUSTER_IDLE_THRESHOLD": 5, "CPU_CLUSTER_BUSY_THRESHOLD": 25}
    )

    assert res["cpu_clusters_count"] >= 1
    assert "cpu_features_df" in res
    assert set(res["cpu_features_df"].columns) >= {
        "mean_%user",
        "mean_%system",
        "p95_%user",
        "p95_%system",
    }
    summary_ids = {item["Status"] for item in res["cpu_clusters_summary"]}
    assert summary_ids & {"Busy (High Load)", "Idle (Background)"}
