# -*- coding: utf-8 -*-
"""Reusable flamegraph summary helpers.

These consolidate common workflows used by MCP tools and examples:
- summarize top symbols/stacks with optional process and symbol filters
- subset-by-symbol summaries
- path statistics via Trie
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Optional, Pattern, Sequence

from .analyzer import FoldedAnalyzer, SymbolFilter, SymbolShare, StackShare
from .io import parse_folded_file, parse_folded_lines
from .api import analyze_lines, analyze_file, analyze_mapping, subset_mapping_by_symbol
from .trie import build_trie_from_collapsed, build_trie_from_file


def _compile_regex(expr: Optional[str]) -> Optional[Pattern[str]]:
    if not expr:
        return None
    return re.compile(expr)


def _proc_match(stack: str, proc_prefix: Optional[str], proc_regex: Optional[Pattern[str]]) -> bool:
    if proc_prefix is None and proc_regex is None:
        return True
    if not stack:
        return False
    proc = stack.split(";", 1)[0]
    if proc_prefix is not None and not proc.startswith(proc_prefix):
        return False
    if proc_regex is not None and re.search(proc_regex, proc) is None:
        return False
    return True


def summarize_analyzer(
    analyzer: FoldedAnalyzer,
    *,
    topk_symbols: int = 20,
    topk_stacks: int = 20,
    order: str = "inclusive",
    symbol_filter: Optional[SymbolFilter] = None,
    proc_prefix: Optional[str] = None,
    proc_regex: Optional[str] = None,
) -> Dict[str, Any]:
    if topk_symbols < 0 or topk_stacks < 0:
        raise ValueError("topk must be non-negative")
    if order not in ("inclusive", "leaf"):
        raise ValueError("order must be 'inclusive' or 'leaf'")
    cregex = _compile_regex(proc_regex)

    sym_stats = analyzer.topk_symbols(
        k=topk_symbols, by=order, proc_prefix=proc_prefix, proc_regex=cregex, filters=symbol_filter
    )
    sym_shares = analyzer.to_symbol_shares(sym_stats)

    stacks = analyzer.topk_stacks(k=topk_stacks)
    if proc_prefix or cregex:
        stacks = [s for s in stacks if _proc_match(s.stack, proc_prefix, cregex)]
    stack_shares = analyzer.to_stack_shares(stacks)

    def _sym_row(s: SymbolShare) -> Dict[str, Any]:
        return {
            "symbol": s.symbol,
            "inclusive": s.inclusive,
            "leaf": s.leaf,
            "inclusive_pct": s.inclusive_pct,
            "leaf_pct": s.leaf_pct,
        }

    def _stack_row(s: StackShare) -> Dict[str, Any]:
        return {
            "stack": s.stack,
            "weight": s.weight,
            "weight_pct": s.weight_pct,
        }

    return {
        "total_weight": analyzer.total_weight,
        "top_symbols": [_sym_row(s) for s in sym_shares],
        "top_stacks": [_stack_row(s) for s in stack_shares],
    }


def summarize_file(
    path: str,
    *,
    topk_symbols: int = 20,
    topk_stacks: int = 20,
    order: str = "inclusive",
    include_prefixes: Optional[Sequence[str]] = None,
    include_suffixes: Optional[Sequence[str]] = None,
    exclude_prefixes: Optional[Sequence[str]] = None,
    exclude_suffixes: Optional[Sequence[str]] = None,
    proc_prefix: Optional[str] = None,
    proc_regex: Optional[str] = None,
) -> Dict[str, Any]:
    filt = None
    if any([include_prefixes, include_suffixes, exclude_prefixes, exclude_suffixes]):
        filt = SymbolFilter(
            include_prefixes=tuple(include_prefixes or ()),
            include_suffixes=tuple(include_suffixes or ()),
            exclude_prefixes=tuple(exclude_prefixes or ()),
            exclude_suffixes=tuple(exclude_suffixes or ()),
        )
    analyzer = analyze_file(path)
    return summarize_analyzer(
        analyzer,
        topk_symbols=topk_symbols,
        topk_stacks=topk_stacks,
        order=order,
        symbol_filter=filt,
        proc_prefix=proc_prefix,
        proc_regex=proc_regex,
    )


def summarize_text(
    text: str,
    *,
    topk_symbols: int = 20,
    topk_stacks: int = 20,
    order: str = "inclusive",
    include_prefixes: Optional[Sequence[str]] = None,
    include_suffixes: Optional[Sequence[str]] = None,
    exclude_prefixes: Optional[Sequence[str]] = None,
    exclude_suffixes: Optional[Sequence[str]] = None,
    proc_prefix: Optional[str] = None,
    proc_regex: Optional[str] = None,
) -> Dict[str, Any]:
    filt = None
    if any([include_prefixes, include_suffixes, exclude_prefixes, exclude_suffixes]):
        filt = SymbolFilter(
            include_prefixes=tuple(include_prefixes or ()),
            include_suffixes=tuple(include_suffixes or ()),
            exclude_prefixes=tuple(exclude_prefixes or ()),
            exclude_suffixes=tuple(exclude_suffixes or ()),
        )
    analyzer = analyze_lines(text.splitlines())
    return summarize_analyzer(
        analyzer,
        topk_symbols=topk_symbols,
        topk_stacks=topk_stacks,
        order=order,
        symbol_filter=filt,
        proc_prefix=proc_prefix,
        proc_regex=proc_regex,
    )


def summarize_mapping(
    stacks: Dict[str, int],
    *,
    topk_symbols: int = 20,
    topk_stacks: int = 20,
    order: str = "inclusive",
    include_prefixes: Optional[Sequence[str]] = None,
    include_suffixes: Optional[Sequence[str]] = None,
    exclude_prefixes: Optional[Sequence[str]] = None,
    exclude_suffixes: Optional[Sequence[str]] = None,
    proc_prefix: Optional[str] = None,
    proc_regex: Optional[str] = None,
) -> Dict[str, Any]:
    filt = None
    if any([include_prefixes, include_suffixes, exclude_prefixes, exclude_suffixes]):
        filt = SymbolFilter(
            include_prefixes=tuple(include_prefixes or ()),
            include_suffixes=tuple(include_suffixes or ()),
            exclude_prefixes=tuple(exclude_prefixes or ()),
            exclude_suffixes=tuple(exclude_suffixes or ()),
        )
    analyzer = analyze_mapping(stacks)
    return summarize_analyzer(
        analyzer,
        topk_symbols=topk_symbols,
        topk_stacks=topk_stacks,
        order=order,
        symbol_filter=filt,
        proc_prefix=proc_prefix,
        proc_regex=proc_regex,
    )


def subset_summary_from_file(
    path: str,
    symbol: str,
    *,
    topk_symbols: int = 20,
    topk_stacks: int = 20,
    order: str = "inclusive",
    include_prefixes: Optional[Sequence[str]] = None,
    include_suffixes: Optional[Sequence[str]] = None,
    exclude_prefixes: Optional[Sequence[str]] = None,
    exclude_suffixes: Optional[Sequence[str]] = None,
    proc_prefix: Optional[str] = None,
    proc_regex: Optional[str] = None,
) -> Dict[str, Any]:
    if not symbol:
        raise ValueError("symbol is required")
    stacks = parse_folded_file(path)
    subset = subset_mapping_by_symbol(stacks, symbol)
    return summarize_mapping(
        subset,
        topk_symbols=topk_symbols,
        topk_stacks=topk_stacks,
        order=order,
        include_prefixes=include_prefixes,
        include_suffixes=include_suffixes,
        exclude_prefixes=exclude_prefixes,
        exclude_suffixes=exclude_suffixes,
        proc_prefix=proc_prefix,
        proc_regex=proc_regex,
    )


def path_stats_from_file(path: str, limit: int = 200) -> Dict[str, Any]:
    if limit < 0:
        raise ValueError("limit must be non-negative")
    trie = build_trie_from_file(path)
    stats = trie.to_path_stats()
    truncated = False
    if limit:
        truncated = len(stats) > limit
        stats = stats[:limit]
    rows = [
        {"path": p, "count": c, "percent": pct}
        for p, c, pct in stats
    ]
    return {"total": trie.total, "paths": rows, "truncated": truncated}


def path_stats_from_text(text: str, limit: int = 200) -> Dict[str, Any]:
    if limit < 0:
        raise ValueError("limit must be non-negative")
    collapsed = parse_folded_lines(text.splitlines())
    trie = build_trie_from_collapsed(collapsed)
    stats = trie.to_path_stats()
    truncated = False
    if limit:
        truncated = len(stats) > limit
        stats = stats[:limit]
    rows = [
        {"path": p, "count": c, "percent": pct}
        for p, c, pct in stats
    ]
    return {"total": trie.total, "paths": rows, "truncated": truncated}


__all__ = [
    "summarize_analyzer",
    "summarize_file",
    "summarize_text",
    "summarize_mapping",
    "subset_summary_from_file",
    "path_stats_from_file",
    "path_stats_from_text",
]
