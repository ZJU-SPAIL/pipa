# -*- coding: utf-8 -*-
from __future__ import annotations

import os

from pipa.analysis.flamegraph.io import parse_folded_file
from pipa.analysis.flamegraph.analyzer import FoldedAnalyzer
from pipa.analysis.flamegraph.api import analyze_file


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
SMALL_FOLDED = os.path.join(DATA_DIR, "out.stacks-folded")
LARGE_FOLDED = os.path.join(DATA_DIR, "out.py.stacks-folded")


def test_parse_folded_file_smoke():
    stacks = parse_folded_file(SMALL_FOLDED)
    assert isinstance(stacks, dict)
    assert len(stacks) > 0
    # Each key must have a positive integer weight
    assert all(isinstance(w, int) and w > 0 for w in stacks.values())


def test_topk_stacks_and_totals():
    stacks = parse_folded_file(SMALL_FOLDED)
    analyzer = FoldedAnalyzer.from_collapsed(stacks)
    assert analyzer.total_weight == sum(stacks.values())
    top5 = analyzer.topk_stacks(5)
    assert 0 < len(top5) <= 5
    # Sorted by weight desc
    for i in range(1, len(top5)):
        assert top5[i - 1].weight >= top5[i].weight


def test_facade_analyze_file():
    analyzer = analyze_file(SMALL_FOLDED)
    assert analyzer.total_weight > 0
    # sanity topk
    assert len(analyzer.topk_symbols(3)) > 0


def test_symbol_hotspots_and_share():
    stacks = parse_folded_file(SMALL_FOLDED)
    analyzer = FoldedAnalyzer(stacks)
    stats = analyzer.symbol_hotspots()
    assert len(stats) > 0
    # Inclusive >= leaf for every symbol
    assert all(s.inclusive >= s.leaf for s in stats)
    # Shares are within [0, 1]
    share0 = analyzer.symbol_share(stats[0].symbol)
    assert 0.0 <= share0 <= 1.0


def test_children_hotspots_contract():
    stacks = parse_folded_file(SMALL_FOLDED)
    analyzer = FoldedAnalyzer(stacks)
    # pick a parent with children present
    parent = None
    for k in stacks.keys():
        frames = k.split(";")
        if len(frames) >= 3:
            parent = frames[1]
            break
    assert parent is not None
    children = analyzer.children_hotspots(parent)
    # Every child hotspot must be a symbol (non-empty) and have non-negative costs
    assert all(c.symbol and c.inclusive >= 0 and c.leaf >= 0 for c in children)
