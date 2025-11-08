# -*- coding: utf-8 -*-
"""
Thin facade API to unify parser and analyzer while keeping them decoupled.

This module depends on both sides and exposes simple high-level entry points.
"""
from __future__ import annotations

from typing import Dict, Mapping, Iterable

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
