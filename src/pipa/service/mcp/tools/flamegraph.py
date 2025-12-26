# -*- coding: utf-8 -*-
"""Flamegraph-related MCP tools registration."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence

from fastmcp import FastMCP

from pipa.analysis.flamegraph import (
    SymbolFilter,
    SymbolShare,
    StackShare,
    analyze_file,
    analyze_lines,
    analyze_mapping,
    build_trie_from_collapsed,
    build_trie_from_file,
    collapse_file_to_mapping,
    parse_folded_file,
    parse_folded_lines,
    subset_mapping_by_symbol,
)
from pipa.parser.flamegraph.stackcollapse_perf import CollapseOptions, format_collapsed


# -----------------
# Helpers
# -----------------


def _validate_topk(v: int, name: str) -> int:
    if v < 0:
        raise ValueError(f"{name} must be >= 0")
    return v


def _validate_order(order: str) -> str:
    if order not in ("inclusive", "leaf"):
        raise ValueError("order must be 'inclusive' or 'leaf'")
    return order


def _make_filter(
    include_prefixes: Optional[Sequence[str]] = None,
    include_suffixes: Optional[Sequence[str]] = None,
    exclude_prefixes: Optional[Sequence[str]] = None,
    exclude_suffixes: Optional[Sequence[str]] = None,
) -> Optional[SymbolFilter]:
    if not any(
        [include_prefixes, include_suffixes, exclude_prefixes, exclude_suffixes]
    ):
        return None
    return SymbolFilter(
        include_prefixes=tuple(include_prefixes or ()),
        include_suffixes=tuple(include_suffixes or ()),
        exclude_prefixes=tuple(exclude_prefixes or ()),
        exclude_suffixes=tuple(exclude_suffixes or ()),
    )


def _symbol_share_row(share: SymbolShare) -> Dict[str, Any]:
    return {
        "symbol": share.symbol,
        "inclusive": share.inclusive,
        "leaf": share.leaf,
        "inclusive_pct": share.inclusive_pct,
        "leaf_pct": share.leaf_pct,
    }


def _stack_share_row(share: StackShare) -> Dict[str, Any]:
    return {
        "stack": share.stack,
        "weight": share.weight,
        "weight_pct": share.weight_pct,
    }


def _summaries(
    analyzer,
    topk_symbols: int,
    topk_stacks: int,
    order: str,
    filt: Optional[SymbolFilter],
) -> Dict[str, Any]:
    sym_shares = analyzer.to_symbol_shares(
        analyzer.topk_symbols(k=topk_symbols, by=order, filters=filt)
    )
    stack_shares = analyzer.to_stack_shares(analyzer.topk_stacks(k=topk_stacks))
    return {
        "total_weight": analyzer.total_weight,
        "top_symbols": [_symbol_share_row(s) for s in sym_shares],
        "top_stacks": [_stack_share_row(s) for s in stack_shares],
    }


# -----------------
# Core implementations (callable directly or via MCP tools)
# -----------------


def analyze_folded_file_impl(
    path: str,
    topk_symbols: int = 20,
    topk_stacks: int = 20,
    order: str = "inclusive",
    include_prefixes: Optional[List[str]] = None,
    include_suffixes: Optional[List[str]] = None,
    exclude_prefixes: Optional[List[str]] = None,
    exclude_suffixes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    _validate_topk(topk_symbols, "topk_symbols")
    _validate_topk(topk_stacks, "topk_stacks")
    order = _validate_order(order)
    filt = _make_filter(
        include_prefixes, include_suffixes, exclude_prefixes, exclude_suffixes
    )
    analyzer = analyze_file(path)
    return _summaries(analyzer, topk_symbols, topk_stacks, order, filt)


def analyze_folded_text_impl(
    text: str,
    topk_symbols: int = 20,
    topk_stacks: int = 20,
    order: str = "inclusive",
    include_prefixes: Optional[List[str]] = None,
    include_suffixes: Optional[List[str]] = None,
    exclude_prefixes: Optional[List[str]] = None,
    exclude_suffixes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    _validate_topk(topk_symbols, "topk_symbols")
    _validate_topk(topk_stacks, "topk_stacks")
    order = _validate_order(order)
    filt = _make_filter(
        include_prefixes, include_suffixes, exclude_prefixes, exclude_suffixes
    )
    analyzer = analyze_lines(text.splitlines())
    return _summaries(analyzer, topk_symbols, topk_stacks, order, filt)


def collapse_perf_script_impl(
    path: str,
    include_pid: bool = False,
    include_tid: bool = False,
    kernel: bool = False,
    jit: bool = False,
    annotate_all: bool = False,
    addrs: bool = False,
    event_filter: str = "",
    do_inline: bool = False,
    context: bool = False,
    srcline: bool = False,
    limit: int = 200,
) -> Dict[str, Any]:
    _validate_topk(limit, "limit")
    options = CollapseOptions(
        include_pid=include_pid,
        include_tid=include_tid,
        kernel=kernel,
        jit=jit,
        annotate_all=annotate_all,
        addrs=addrs,
        event_filter=event_filter,
        do_inline=do_inline,
        context=context,
        srcline=srcline,
    )
    collapsed = collapse_file_to_mapping(path, options)
    lines = format_collapsed(collapsed)
    if limit:
        lines = lines[:limit]
    return {
        "total_weight": sum(collapsed.values()),
        "unique_stacks": len(collapsed),
        "lines": lines,
    }


def symbol_overhead_impl(
    path: str,
    symbol: str,
    depth: Optional[int] = None,
    fuzzy: bool = False,
) -> Dict[str, Any]:
    if not symbol:
        raise ValueError("symbol is required")
    trie = build_trie_from_file(path)
    rows = trie.query_symbol_overhead(symbol, k=depth, fuzzy=fuzzy)
    return {"total": trie.total, "results": rows}


def export_call_tree_impl(
    path: str,
    start_symbol: Optional[str] = None,
    fuzzy: bool = False,
    depth: Optional[int] = None,
) -> Dict[str, Any]:
    trie = build_trie_from_file(path)
    trees = trie.export_sorted_tree(start_symbol=start_symbol, fuzzy=fuzzy, k=depth)
    return {"total": trie.total, "trees": trees}


def subset_analyze_impl(
    path: str,
    symbol: str,
    topk_symbols: int = 20,
    topk_stacks: int = 20,
    order: str = "inclusive",
) -> Dict[str, Any]:
    if not symbol:
        raise ValueError("symbol is required")
    _validate_topk(topk_symbols, "topk_symbols")
    _validate_topk(topk_stacks, "topk_stacks")
    order = _validate_order(order)
    collapsed = parse_folded_file(path)
    subset = subset_mapping_by_symbol(collapsed, symbol)
    analyzer = analyze_mapping(subset)
    return _summaries(analyzer, topk_symbols, topk_stacks, order, None)


def analyze_folded_lines_impl(
    lines: Iterable[str],
    topk_symbols: int = 20,
    topk_stacks: int = 20,
    order: str = "inclusive",
) -> Dict[str, Any]:
    _validate_topk(topk_symbols, "topk_symbols")
    _validate_topk(topk_stacks, "topk_stacks")
    order = _validate_order(order)
    analyzer = analyze_lines(lines)
    return _summaries(analyzer, topk_symbols, topk_stacks, order, None)


def folded_text_to_trie_impl(
    text: str,
    depth: Optional[int] = None,
) -> Dict[str, Any]:
    collapsed = parse_folded_lines(text.splitlines())
    trie = build_trie_from_collapsed(collapsed)
    trees = trie.export_sorted_tree(k=depth)
    return {"total": trie.total, "trees": trees}


# -----------------
# Registration
# -----------------


def register_flamegraph_tools(mcp: FastMCP) -> None:
    mcp.tool(
        description="Analyze folded stack file and return top symbols/stacks with percentages."
    )(analyze_folded_file_impl)
    mcp.tool(
        description="Analyze folded stack text payload (one stack per line) and return summaries."
    )(analyze_folded_text_impl)
    mcp.tool(
        description="Collapse perf script output into folded stacks (mapping), optionally limiting returned lines."
    )(collapse_perf_script_impl)
    mcp.tool(
        description="Query overhead for a symbol from a folded stack file using Trie traversal."
    )(symbol_overhead_impl)
    mcp.tool(
        description="Export a sorted call tree (heaviest first) from a folded stack file."
    )(export_call_tree_impl)
    mcp.tool(
        description="Subset folded stacks by symbol then analyze top symbols/stacks."
    )(subset_analyze_impl)
    mcp.tool(
        description="Analyze folded stacks provided as lines (iterable) and return summaries. Internal helper exposed for automation."
    )(analyze_folded_lines_impl)
    mcp.tool(
        description="Collapse folded text (already folded) into mapping and return a Trie export."
    )(folded_text_to_trie_impl)


__all__ = [
    "register_flamegraph_tools",
    "analyze_folded_file_impl",
    "analyze_folded_text_impl",
    "collapse_perf_script_impl",
    "symbol_overhead_impl",
    "export_call_tree_impl",
    "subset_analyze_impl",
    "analyze_folded_lines_impl",
    "folded_text_to_trie_impl",
]
