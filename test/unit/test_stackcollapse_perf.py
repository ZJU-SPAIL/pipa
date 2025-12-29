# -*- coding: utf-8 -*-
from pathlib import Path
import subprocess
import tempfile
import pytest

from pipa.parser.flamegraph.stackcollapse_perf import (
    CollapseOptions,
    collapse_file,
    save_collapsed,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
INPUT_PATH = DATA_DIR / "perf_script_file.txt"
EXPECTED_PATH = DATA_DIR / "out.stacks-folded"


@pytest.mark.skipif(not INPUT_PATH.exists(), reason="perf_script_file.txt not found")
@pytest.mark.skipif(not EXPECTED_PATH.exists(), reason="expected output not found")
def test_stackcollapse_output_matches_expected():
    options = CollapseOptions(
        include_pid=False,
        include_tid=False,
        kernel=False,
        jit=False,
        annotate_all=False,
        addrs=False,
        event_filter="",
        do_inline=False,
        context=False,
        srcline=False,
    )
    collapsed = collapse_file(INPUT_PATH, options)
    with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as tmp:
        tmp_path = Path(tmp.name)
    try:
        save_collapsed(collapsed, str(tmp_path))
        # 使用系统 diff 验证（-u 统一格式），输出差异以便调试
        proc = subprocess.run(
            ["diff", "-u", str(EXPECTED_PATH), str(tmp_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert (
            proc.returncode == 0
        ), f"Output differs from expected. Diff:\n{proc.stdout}"
    finally:
        tmp_path.unlink(missing_ok=True)
