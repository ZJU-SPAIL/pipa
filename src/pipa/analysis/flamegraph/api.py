# -*- coding: utf-8 -*-
"""
Thin facade API to unify parser and analyzer while keeping them decoupled.

This module depends on both sides and exposes simple high-level entry points.
"""
from __future__ import annotations

from typing import Dict, Mapping, Iterable, Sequence

from pipa.analysis.flamegraph.io import parse_folded_file, parse_folded_lines
from pipa.analysis.flamegraph.analyzer import FoldedAnalyzer
from pipa.parser.flamegraph.stackcollapse_perf import (
    CollapseOptions,
    collapse,
    collapse_file,
)


# --------------- Collapse to mapping ---------------


def collapse_to_mapping(
    lines: Iterable[str], options: CollapseOptions
) -> Dict[str, int]:
    return collapse(lines, options)


def collapse_file_to_mapping(path: str, options: CollapseOptions) -> Dict[str, int]:
    return collapse_file(path, options)


# --------------- Analyze from mapping or file ---------------


def analyze_mapping(stacks: Mapping[str, int]) -> FoldedAnalyzer:
    return FoldedAnalyzer.from_collapsed(stacks)


def analyze_file(path: str) -> FoldedAnalyzer:
    stacks = parse_folded_file(path)
    return FoldedAnalyzer.from_collapsed(stacks)


def analyze_lines(lines: Iterable[str]) -> FoldedAnalyzer:
    stacks = parse_folded_lines(lines)
    return FoldedAnalyzer.from_collapsed(stacks)


def analyze_collapse_file(path: str, options: CollapseOptions) -> FoldedAnalyzer:
    stacks = collapse_file_to_mapping(path, options)
    return FoldedAnalyzer.from_collapsed(stacks)


# --------------- Subset helpers ---------------


def subset_mapping_by_symbol(
    stacks: Mapping[str, int], symbol: str, contains_fallback: bool = True
) -> Dict[str, int]:
    subset: Dict[str, int] = {}
    for k, w in stacks.items():
        parts = k.split(";")
        if len(parts) >= 2 and symbol in parts[1:]:
            subset[k] = subset.get(k, 0) + w
        elif contains_fallback and symbol in k:
            subset[k] = subset.get(k, 0) + w
    return subset


def analyzer_from_symbol_subset(
    stacks: Mapping[str, int], symbol: str, contains_fallback: bool = True
) -> FoldedAnalyzer:
    return FoldedAnalyzer.from_collapsed(
        subset_mapping_by_symbol(stacks, symbol, contains_fallback)
    )


def filter_stacks_by_prefixes(
    analyzer: FoldedAnalyzer, prefixes: Sequence[str], k: int = 1000
):
    return analyzer.filter_stacks_by_prefixes(prefixes, k)
