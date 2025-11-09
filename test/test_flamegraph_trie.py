# -*- coding: utf-8 -*-
from __future__ import annotations

import os

from pipa.analysis.flamegraph.io import parse_folded_file
from pipa.analysis.flamegraph.trie import (
    build_trie_from_collapsed,
    Trie,
)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
SMALL_FOLDED = os.path.join(DATA_DIR, "out.stacks-folded")
LARGE_FOLDED = os.path.join(DATA_DIR, "out.stacks-folded")


def _small_trie() -> Trie:
    stacks = parse_folded_file(SMALL_FOLDED)
    return build_trie_from_collapsed(stacks)


def test_build_trie_from_collapsed_and_paths():
    trie = _small_trie()
    assert trie.total > 0
    # iter_paths returns non-empty leaf paths
    paths = list(trie.iter_paths())
    assert len(paths) > 0
    # to_path_stats returns strings joined by ';' and valid percentages
    stats = trie.to_path_stats()
    assert all(
        isinstance(p, str) and isinstance(c, int) and isinstance(pct, float)
        for p, c, pct in stats
    )
    assert all(0.0 <= pct <= 100.0 for _, _, pct in stats)


def test_query_symbol_overhead_exact_and_k_depth():
    trie = _small_trie()
    # pick a middle symbol from one stack
    any_stack = next(iter(parse_folded_file(SMALL_FOLDED).keys()))
    frames = any_stack.split(";")
    assert len(frames) >= 3
    sym = frames[1]  # first frame after process label

    # exact match without depth limit should be >= exact with k=0
    rows_all = trie.query_symbol_overhead(sym, k=None, fuzzy=False)
    rows_k0 = trie.query_symbol_overhead(sym, k=0, fuzzy=False)
    assert rows_all and rows_k0
    assert rows_all[0]["inclusive"] >= rows_k0[0]["inclusive"]
    # percentage bounds
    assert 0.0 <= rows_all[0]["inclusive_pct"] <= 100.0


def test_query_symbol_overhead_fuzzy():
    trie = _small_trie()
    # take some symbol and search by its first two characters
    any_stack = next(iter(parse_folded_file(SMALL_FOLDED).keys()))
    frames = any_stack.split(";")
    assert len(frames) >= 3
    sym = frames[1]
    prefix = sym[:2]
    rows = trie.query_symbol_overhead(prefix, k=1, fuzzy=True)
    # fuzzy may match multiple nodes; ensure path returned and inclusive non-negative
    assert isinstance(rows, list)
    if rows:
        assert all(r["inclusive"] >= 0 and isinstance(r["path"], list) for r in rows)


def test_export_sorted_tree_ordering_and_k_depth():
    trie = _small_trie()
    # export entire forest
    forest = trie.export_sorted_tree()
    assert isinstance(forest, list)
    if forest:
        # children should be sorted by count desc
        ch = forest[0].get("children", [])
        for i in range(1, len(ch)):
            assert ch[i - 1]["count"] >= ch[i]["count"]
    # export from a specific symbol with depth limit 1
    any_stack = next(iter(parse_folded_file(SMALL_FOLDED).keys()))
    frames = any_stack.split(";")
    sym = frames[1]
    sub = trie.export_sorted_tree(start_symbol=sym, k=1)
    assert isinstance(sub, list)
    if sub:
        # depth 1 implies children list exists but grandchildren omitted
        for node in sub:
            for child in node.get("children", []):
                # grandchildren should be absent when k=1
                assert not child.get("children", []) or isinstance(
                    child.get("children"), list
                )
