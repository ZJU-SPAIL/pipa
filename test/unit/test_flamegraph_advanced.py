# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import re

from pipa.analysis.flamegraph.io import parse_folded_file
from pipa.analysis.flamegraph.analyzer import (
    FoldedAnalyzer,
    SymbolFilter,
)
from pipa.analysis.flamegraph.csv_export import (
    write_symbol_stats_csv,
    write_stack_stats_csv,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
SMALL_FOLDED = DATA_DIR / "out.stacks-folded"


def _mk_analyzer():
    stacks = parse_folded_file(SMALL_FOLDED)
    return FoldedAnalyzer.from_collapsed(stacks)


def test_symbol_filter_include_exclude_prefix_suffix():
    an = _mk_analyzer()
    filt = SymbolFilter(include_prefixes=("do_",), exclude_suffixes=("_fault",))
    stats = an.topk_symbols(k=50, filters=filt)
    assert all(
        s.symbol.startswith("do_") and not s.symbol.endswith("_fault") for s in stats
    )


def test_proc_regex_filter():
    an = _mk_analyzer()
    stats = an.topk_symbols(k=10, proc_regex=re.compile(r"^ewp_"))
    # if there are ewp_ prefixed processes, results should be non-empty
    # otherwise it's acceptable to be empty but should not error
    assert stats is not None


def test_children_filter_and_path_slicing():
    an = _mk_analyzer()
    # find a parent that exists
    parent = None
    stacks = list(an.iter_items())
    for k, w in stacks:
        frames = k.split(";")
        if len(frames) >= 4:
            parent = frames[2]  # some middle frame
            break
    assert parent is not None
    # children under filter (include prefix)
    filt = SymbolFilter(include_prefixes=(parent[:2],))
    children = an.children_hotspots(parent_symbol=parent, filters=filt)
    assert all(c.symbol.startswith(parent[:2]) for c in children)

    # path prefix subset
    frames = stacks[0][0].split(";")[1:3]
    sub = an.subset_by_path_prefix(frames)
    for s, w in sub.iter_items():
        syms = s.split(";")[1:]
        assert syms[: len(frames)] == frames

    # path suffix subset
    frames2 = stacks[0][0].split(";")[-3:]
    sub2 = an.subset_by_path_suffix(frames2[1:])
    for s, w in sub2.iter_items():
        syms = s.split(";")[1:]
        assert syms[-len(frames2[1:]) :] == frames2[1:]


def test_dso_aggregation_and_csv_export(tmp_path):
    an = _mk_analyzer()

    # naive resolver: group unknowns vs others by bracketed notation
    def resolver(sym: str) -> str:
        if sym.startswith("[") and sym.endswith("]"):
            return sym
        # else group into "user"
        return "<user>"

    dso_stats = an.aggregate_by_dso(resolver)
    assert isinstance(dso_stats, list)
    # export top symbols and top stacks
    sym_stats = an.topk_symbols(10)
    stack_stats = an.topk_stacks(10)

    sym_csv = tmp_path / "sym.csv"
    stack_csv = tmp_path / "stack.csv"
    write_symbol_stats_csv(str(sym_csv), sym_stats)
    write_stack_stats_csv(str(stack_csv), stack_stats)

    assert sym_csv.exists()
    assert stack_csv.exists()
    # check CSV header
    with open(sym_csv, "r", encoding="utf-8") as f:
        header = f.readline().strip()
        assert header == "symbol,inclusive,leaf"
    with open(stack_csv, "r", encoding="utf-8") as f:
        header = f.readline().strip()
        assert header == "stack,weight"


def test_to_shares_and_csv_with_pct(tmp_path):
    an = _mk_analyzer()
    sym_stats = an.topk_symbols(5)
    stack_stats = an.topk_stacks(5)

    sym_shares = an.to_symbol_shares(sym_stats)
    stack_shares = an.to_stack_shares(stack_stats)

    # values in [0,100]
    assert all(
        0.0 <= s.inclusive_pct <= 100.0 and 0.0 <= s.leaf_pct <= 100.0
        for s in sym_shares
    )
    assert all(0.0 <= s.weight_pct <= 100.0 for s in stack_shares)

    sym_csv = tmp_path / "sym_pct.csv"
    stack_csv = tmp_path / "stack_pct.csv"

    write_symbol_stats_csv(str(sym_csv), sym_shares)
    write_stack_stats_csv(str(stack_csv), stack_shares)

    with open(sym_csv, "r", encoding="utf-8") as f:
        header = f.readline().strip()
        row = f.readline().strip()
        assert header == "symbol,inclusive,inclusive_pct,leaf,leaf_pct"
        assert "%" in row
    with open(stack_csv, "r", encoding="utf-8") as f:
        header = f.readline().strip()
        row = f.readline().strip()
        assert header == "stack,weight,weight_pct"
        assert "%" in row
