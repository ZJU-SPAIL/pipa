# -*- coding: utf-8 -*-
import os
import subprocess
import tempfile
import pytest

from pipa.parser.flamegraph.stackcollapse_perf import (
    CollapseOptions,
    collapse_file,
    save_collapsed,
)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
INPUT_PATH = os.path.join(DATA_DIR, "perf_script_file.txt")
EXPECTED_PATH = os.path.join(DATA_DIR, "out.py.stacks-folded")


@pytest.mark.skipif(
    not os.path.exists(INPUT_PATH), reason="perf_script_file.txt not found"
)
@pytest.mark.skipif(
    not os.path.exists(EXPECTED_PATH), reason="expected output not found"
)
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
        tmp_path = tmp.name
    try:
        save_collapsed(collapsed, tmp_path)
        # 使用系统 diff 验证（-u 统一格式），输出差异以便调试
        proc = subprocess.run(
            ["diff", "-u", EXPECTED_PATH, tmp_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert (
            proc.returncode == 0
        ), f"Output differs from expected. Diff:\n{proc.stdout}"
    finally:
        os.unlink(tmp_path)
