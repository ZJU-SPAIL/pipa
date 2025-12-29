import pandas as pd

from pipa.report.context_builder import (
    _format_cpu_list_to_range,
    _parse_cpu_list_str,
    build_full_context,
)


def test_parse_and_format_cpu_list():
    cpus = _parse_cpu_list_str("0-2,5,7-8")
    assert cpus == {"0", "1", "2", "5", "7", "8"}
    assert _format_cpu_list_to_range([0, 1, 2, 4, 5, 7]) == "0-2,4-5,7"


def test_build_full_context_defaults():
    ctx = build_full_context({}, {})
    assert ctx["num_cpu"] == 1
    assert ctx["total_cpu"] == 0.0
    assert ctx["cpu_clusters_count"] == 0


def test_build_full_context_sar_cpu_and_disk():
    sar_cpu = pd.DataFrame(
        {
            "CPU": ["0", "1", "2", "3", "all"],
            "%user": [5, 20, 30, 40, 25],
            "%system": [5, 5, 5, 5, 5],
            "%iowait": [1, 2, 3, 4, 2.5],
            "%idle": [89, 73, 62, 51, 65],
        }
    )
    sar_disk = pd.DataFrame(
        {
            "DEV": ["sda", "sdb"],
            "%util": [50, 10],
            "await": [2.0, 1.0],
            "avgqu-sz": [0.5, 0.1],
            "rkB/s": [1024, 0],
            "wkB/s": [0, 512],
        }
    )
    ctx = build_full_context(
        {"sar_cpu": sar_cpu, "sar_disk": sar_disk},
        {
            "disk_info": {
                "block_devices": [
                    {"name": "sda", "rotational": "SSD", "size_bytes": 1024}
                ]
            }
        },
    )
    assert ctx["cpu_clusters_count"] >= 1
    assert ctx["total_cpu"] > 0
    assert ctx["busiest_disk_name"] == "sda"
    assert ctx["busiest_disk_subtype"] in {"NVME_SSD", "SATA_SSD", "SSD"}
