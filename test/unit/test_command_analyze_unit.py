from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


def _dummy_fig(name="fig"):
    return SimpleNamespace(to_html=lambda **kwargs: f"<div>{name}</div>", data=[1])


@pytest.fixture()
def level_dir(tmp_path: Path) -> Path:
    level = tmp_path / "attach_session"
    level.mkdir()
    static_info = tmp_path / "static_info.yaml"
    static_info.write_text(
        """
    disk_info:
      block_devices: []
    os_info:
      kernel: test
    """
    )
    return level


@pytest.fixture()
def common_patches():
    perf_df_events = pd.DataFrame(
        {
            "timestamp": [1.0, 2.0],
            "cpu": ["CPU0", "CPU0"],
            "event_name": ["cycles", "instructions"],
            "value": [1, 2],
            "unit": ["", ""],
            "type": ["event", "event"],
        }
    )
    perf_df_metrics = pd.DataFrame(
        {
            "timestamp": [1.0],
            "cpu": ["CPU0"],
            "metric_name": ["IPC"],
            "value": [3.14],
            "type": ["metric"],
        }
    )
    parser_registry = {
        "perf_stat": MagicMock(
            return_value={"events": perf_df_events, "metrics": perf_df_metrics}
        ),
        "sar_cpu": MagicMock(
            return_value=pd.DataFrame(
                {
                    "timestamp": [1, 2],
                    "CPU": ["-1", "-1"],
                    "%user": [10, 20],
                    "%system": [5, 5],
                    "%idle": [85, 75],
                }
            )
        ),
    }

    build_full_context = MagicMock(
        return_value={
            "cpu_features_df": pd.DataFrame({"feature": [1, 2]}, index=[0, 1]),
            "cpu_clusters_summary": {"cluster": [0, 1], "count": [1, 1]},
        }
    )

    patches = {
        "PARSER_REGISTRY": patch(
            "pipa.commands.analyze.PARSER_REGISTRY", parser_registry
        ),
        "load_rules": patch("pipa.commands.analyze.load_rules", return_value=([], {})),
        "build_full_context": patch(
            "pipa.commands.analyze.build_full_context", build_full_context
        ),
        "format_rules_to_html_tree": patch(
            "pipa.commands.analyze.format_rules_to_html_tree",
            return_value=("<audit>", "<tree>", "<findings>"),
        ),
        "plot_cpu_clusters": patch(
            "pipa.commands.analyze.plot_cpu_clusters",
            side_effect=lambda *_, **__: _dummy_fig("cpu"),
        ),
        "plot_disk_sunburst": patch(
            "pipa.commands.analyze.plot_disk_sunburst", return_value=_dummy_fig("sun")
        ),
        "plot_per_disk_pies": patch(
            "pipa.commands.analyze.plot_per_disk_pies", return_value=_dummy_fig("pies")
        ),
        "plot_sar_cpu": patch(
            "pipa.commands.analyze.plot_sar_cpu",
            return_value=(_dummy_fig("sarcpu"), {}),
        ),
        "plot_timeseries_generic": patch(
            "pipa.commands.analyze.plot_timeseries_generic",
            return_value=({"sar_cpu": _dummy_fig("ts")}, {}),
        ),
        "extract_hotspots": patch(
            "pipa.commands.analyze.extract_hotspots",
            return_value=[{"symbol": "foo", "samples": 1}],
        ),
        "generate_html_report": patch(
            "pipa.commands.analyze.generate_html_report", autospec=True
        ),
    }
    with (
        patches["PARSER_REGISTRY"],
        patches["load_rules"],
        patches["build_full_context"],
        patches["format_rules_to_html_tree"],
        patches["plot_cpu_clusters"],
        patches["plot_disk_sunburst"],
        patches["plot_per_disk_pies"],
        patches["plot_sar_cpu"],
        patches["plot_timeseries_generic"],
        patches["extract_hotspots"],
        patches["generate_html_report"] as gen_html,
    ):
        yield {"generate_html_report": gen_html}


def _write_sar_cpu(level_dir: Path):
    sar_content = "#hostname;interval;timestamp;CPU;%user;%system;%idle\n"
    sar_content += "test;1;1;-1;10;5;85\n"
    (level_dir / "sar_cpu.csv").write_text(sar_content)


def test_generate_report_happy(level_dir: Path, common_patches, tmp_path: Path):
    from pipa.commands.analyze import _generate_report

    (level_dir / "perf_stat.txt").write_text("1;CPU0;cycles;1; ;event\n")
    _write_sar_cpu(level_dir)
    (level_dir / "perf.data").write_text("binary")

    report_path = tmp_path / "report.html"
    _generate_report(level_dir, report_path)

    gen = common_patches["generate_html_report"]
    gen.assert_called_once()
    kwargs = gen.call_args.kwargs
    assert kwargs["warnings"] == []
    assert "perf" in kwargs["tables_json"]
    assert "hotspots" in kwargs["tables_json"]
    assert kwargs["output_path"] == report_path


def test_generate_report_missing_perf_stat(
    level_dir: Path, common_patches, tmp_path: Path
):
    from pipa.commands.analyze import _generate_report

    _write_sar_cpu(level_dir)
    report_path = tmp_path / "report.html"

    _generate_report(level_dir, report_path)

    kwargs = common_patches["generate_html_report"].call_args.kwargs
    assert any("perf_stat.txt not found" in w for w in kwargs["warnings"])


def test_generate_report_empty_perf_stat(
    level_dir: Path, common_patches, tmp_path: Path
):
    from pipa.commands.analyze import _generate_report

    (level_dir / "perf_stat.txt").write_text("")
    _write_sar_cpu(level_dir)
    report_path = tmp_path / "report.html"

    _generate_report(level_dir, report_path)

    kwargs = common_patches["generate_html_report"].call_args.kwargs
    assert any("perf_stat.txt is empty" in w for w in kwargs["warnings"])


def test_generate_report_missing_static_info(
    level_dir: Path, common_patches, tmp_path: Path
):
    from pipa.commands.analyze import _generate_report

    (level_dir.parent / "static_info.yaml").unlink()
    (level_dir / "perf_stat.txt").write_text("1;CPU0;cycles;1\n")
    _write_sar_cpu(level_dir)
    report_path = tmp_path / "report.html"

    _generate_report(level_dir, report_path)

    kwargs = common_patches["generate_html_report"].call_args.kwargs
    assert any(
        "static_info.yaml/spec_info.yaml not found" in w for w in kwargs["warnings"]
    )
    assert kwargs["static_info_str"] == ""


def test_generate_report_missing_perf_data_file(
    level_dir: Path, common_patches, tmp_path: Path
):
    from pipa.commands.analyze import _generate_report

    (level_dir / "perf_stat.txt").write_text("1;CPU0;cycles;1\n")
    _write_sar_cpu(level_dir)
    report_path = tmp_path / "report.html"

    _generate_report(level_dir, report_path)

    kwargs = common_patches["generate_html_report"].call_args.kwargs
    assert any("perf.data not found" in w for w in kwargs["warnings"])
