import pandas as pd

from pipa.report.plotter import (
    _compress_cpu_ranges,
    _natural_sort,
    plot_cpu_clusters,
    plot_disk_sunburst,
    plot_per_disk_pies,
    plot_sar_cpu,
    plot_timeseries_generic,
)


def test_natural_sort_and_compress():
    assert _natural_sort(["10", "2", "a"]) == ["2", "10", "a"]
    assert _compress_cpu_ranges(["0", "1", "2", "all", "numa_0"]) == [
        "all",
        "numa_0",
        "0-2",
    ]


def test_plot_sar_cpu_filters():
    df = pd.DataFrame(
        {
            "timestamp": [1, 2],
            "CPU": ["0", "1"],
            "%user": [10, 20],
            "%system": [5, 5],
            "%iowait": [1, 2],
            "%idle": [84, 73],
        }
    )
    fig, filters = plot_sar_cpu(df, {"numa_cpu_map": {"numa_0": "0"}})
    assert fig.data
    assert "CPU" in filters and filters["CPU"]["values"]


def test_plot_timeseries_generic_groups_memory():
    df = pd.DataFrame(
        {
            "timestamp": [1, 2],
            "kbmemfree": [1024 * 1024, 2 * 1024 * 1024],
            "%commit": [10, 20],
        }
    )
    plots, filters = plot_timeseries_generic(df, "sar_memory")
    assert any("size_gb" in name for name in filters)
    assert any(fig.data for fig in plots.values())


def test_disk_plots_empty_and_basic():
    empty_fig = plot_disk_sunburst({})
    assert len(empty_fig.data) == 0

    disk_info = {
        "block_devices": [
            {
                "name": "sda",
                "rotational": "SSD",
                "size_bytes": 1024 * 1024,
                "partitions": [
                    {"name": "sda1", "size_bytes": 512 * 1024},
                ],
            }
        ]
    }
    sun = plot_disk_sunburst(disk_info)
    pies = plot_per_disk_pies(disk_info)
    assert len(sun.data) > 0
    assert len(pies.data) > 0


def test_plot_cpu_clusters_basic():
    df = pd.DataFrame(
        {
            "mean_%user": [1.0, 10.0],
            "mean_%system": [1.0, 5.0],
            "mean_%idle": [98.0, 85.0],
            "p95_%idle": [99.0, 90.0],
            "p95_%user": [2.0, 12.0],
            "p95_%system": [2.0, 7.0],
            "cluster_final": [99, 1],
        },
        index=["0", "1"],
    )
    fig = plot_cpu_clusters(df)
    assert fig.data
