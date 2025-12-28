# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import pytest

from pipa.service.mcp.tools import flamegraph as mfg

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
FOLDED = os.path.join(DATA_DIR, "out.stacks-folded")
PERF_SCRIPT = os.path.join(DATA_DIR, "perf_script_file.txt")


@pytest.mark.skipif(not os.path.exists(FOLDED), reason="folded input not found")
def test_analyze_folded_file_topk_and_filters():
    res = mfg.analyze_folded_file_impl(
        FOLDED,
        topk_symbols=3,
        topk_stacks=2,
        order="inclusive",
        include_prefixes=["__"],
        exclude_suffixes=["_end"],
    )
    assert res["total_weight"] > 0
    assert len(res["top_symbols"]) <= 3
    assert len(res["top_stacks"]) <= 2


@pytest.mark.skipif(not os.path.exists(FOLDED), reason="folded input not found")
def test_symbol_overhead_and_call_tree_depth_limits():
    rows = mfg.symbol_overhead_impl(FOLDED, symbol="main", depth=1, fuzzy=True)
    assert "total" in rows and rows["total"] >= 0
    if rows["results"]:
        first = rows["results"][0]
        assert "inclusive_pct" in first and 0.0 <= first["inclusive_pct"] <= 100.0
    tree = mfg.export_call_tree_impl(FOLDED, start_symbol=None, depth=1, max_children=5)
    assert "trees" in tree and isinstance(tree["trees"], list)


@pytest.mark.skipif(not os.path.exists(FOLDED), reason="folded input not found")
def test_subset_analyze_and_tree_export():
    res = mfg.subset_analyze_impl(FOLDED, symbol="main", topk_symbols=4, topk_stacks=3)
    assert res["total_weight"] >= 0
    tree = mfg.export_call_tree_impl(FOLDED, start_symbol=None, depth=1, max_children=5)
    assert tree["total"] >= 0
    assert isinstance(tree["trees"], list)


@pytest.mark.skipif(
    not os.path.exists(PERF_SCRIPT), reason="perf_script_file.txt not found"
)
def test_collapse_perf_script_smoke():
    res = mfg.collapse_perf_script_impl(
        PERF_SCRIPT,
        include_pid=False,
        include_tid=False,
        limit=10,
        topk_symbols=3,
        topk_stacks=2,
    )
    assert res["unique_stacks"] > 0
    assert len(res["lines"]) <= 10
    assert "folded_path" in res and os.path.exists(res["folded_path"])
    assert "summary" in res and res["summary"]["total_weight"] == res["total_weight"]
