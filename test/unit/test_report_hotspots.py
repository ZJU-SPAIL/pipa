from pathlib import Path
from unittest.mock import MagicMock, patch

from pipa.report.hotspots import extract_hotspots


def test_extract_hotspots_missing_file(tmp_path):
    assert extract_hotspots(tmp_path / "missing.data") == []


def test_extract_hotspots_parses_output(tmp_path):
    perf_path = tmp_path / "perf.data"
    perf_path.write_text("dummy")

    stdout = """
    # Overhead  Samples  Command  Shared Object  Symbol
    12.34%  100  cmd  libfoo.so  foo [.] 
    5.00%  50  cmd  [kernel.kallsyms]  __sched_text_start [k]
    """

    mock_run = MagicMock()
    mock_run.returncode = 0
    mock_run.stdout = stdout
    mock_run.stderr = ""

    with patch("pipa.report.hotspots.subprocess.run", return_value=mock_run):
        res = extract_hotspots(perf_path, max_rows=1)

    assert len(res) == 1
    row = res[0]
    assert row["Overhead"] == 12.34
    assert row["Scope"] == "User"
    assert row["Symbol"] == "foo"
