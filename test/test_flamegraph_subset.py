# -*- coding: utf-8 -*-
from __future__ import annotations

import os

from pipa.analysis.flamegraph.io import parse_folded_file
from pipa.analysis.flamegraph.analyzer import FoldedAnalyzer
from pipa.analysis.flamegraph.api import subset_mapping_by_symbol, analyzer_from_symbol_subset, filter_stacks_by_prefixes

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
FOLDED = os.path.join(DATA_DIR, "out.stacks-folded")


def test_subset_by_symbol_log_flusher():
    stacks = parse_folded_file(FOLDED)
    sub = subset_mapping_by_symbol(stacks, "log_flusher")
    assert isinstance(sub, dict)
    assert len(sub) > 0
    an = analyzer_from_symbol_subset(stacks, "log_flusher")
    assert an.total_weight > 0


def test_filter_stacks_by_prefixes():
    stacks = parse_folded_file(FOLDED)
    an = FoldedAnalyzer.from_collapsed(stacks).subset_by_symbol("log_flusher")
    filtered = filter_stacks_by_prefixes(an, ("__x64_sys_", "vfs_", "ext4_"), k=200)
    # All returned stacks must contain at least one of the prefixes in frames
    for s in filtered:
        frames = s.stack.split(";")[1:]
        assert any(any(f.startswith(p) for p in ("__x64_sys_", "vfs_", "ext4_")) for f in frames)
