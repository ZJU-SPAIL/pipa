# -*- coding: utf-8 -*-
"""Flamegraph-related MCP tools registration."""
from __future__ import annotations

from typing import Any, Dict, Optional, List

from fastmcp import FastMCP

from pipa.analysis.flamegraph import (
    build_trie_from_file,
    collapse_file_to_mapping,
)
from pipa.analysis.flamegraph.summary import (
    summarize_file,
    summarize_mapping,
    subset_summary_from_file,
    path_stats_from_file,
)
from pipa.parser.flamegraph.stackcollapse_perf import CollapseOptions, format_collapsed


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
    proc_prefix: Optional[str] = None,
    proc_regex: Optional[str] = None,
) -> Dict[str, Any]:
    return summarize_file(
        path,
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
    output_path: Optional[str] = None,
    topk_symbols: int = 20,
    topk_stacks: int = 20,
    order: str = "inclusive",
) -> Dict[str, Any]:
    if limit < 0:
        raise ValueError("limit must be non-negative")
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
    collapsed = collapse_file_to_mapping(path, options)  # type: ignore[name-defined]
    lines_full = format_collapsed(collapsed)
    total_lines = len(lines_full)
    truncated = False
    lines = lines_full
    if limit:
        truncated = total_lines > limit
        lines = lines_full[:limit]

    folded_path = output_path or f"{path}.folded"
    with open(folded_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines_full))

    summary = summarize_mapping(
        collapsed,
        topk_symbols=topk_symbols,
        topk_stacks=topk_stacks,
        order=order,
    )

    return {
        "folded_path": folded_path,
        "summary": summary,
        "total_weight": sum(collapsed.values()),
        "unique_stacks": len(collapsed),
        "lines": lines,
        "total_lines": total_lines,
        "truncated": truncated,
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
    max_children: Optional[int] = None,
) -> Dict[str, Any]:
    trie = build_trie_from_file(path)
    trees = trie.export_sorted_tree(start_symbol=start_symbol, fuzzy=fuzzy, k=depth)
    if max_children is not None and max_children > 0:

        def trim(node: Dict[str, Any]) -> Dict[str, Any]:
            children = node.get("children", [])
            if isinstance(children, list) and len(children) > max_children:
                node["children"] = children[:max_children]
            for c in node.get("children", []) or []:
                trim(c)
            return node

        trees = [trim(t) for t in trees]
    return {"total": trie.total, "trees": trees}


def subset_analyze_impl(
    path: str,
    symbol: str,
    topk_symbols: int = 20,
    topk_stacks: int = 20,
    order: str = "inclusive",
    include_prefixes: Optional[List[str]] = None,
    include_suffixes: Optional[List[str]] = None,
    exclude_prefixes: Optional[List[str]] = None,
    exclude_suffixes: Optional[List[str]] = None,
    proc_prefix: Optional[str] = None,
    proc_regex: Optional[str] = None,
) -> Dict[str, Any]:
    return subset_summary_from_file(
        path,
        symbol,
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


def path_stats_impl(path: str, limit: int = 200) -> Dict[str, Any]:
    return path_stats_from_file(path, limit=limit)


# -----------------
# Registration
# -----------------


def register_flamegraph_tools(mcp: FastMCP) -> None:
    mcp.tool(
        description="Analyze folded stack file and return top symbols/stacks with percentages. Supports proc filters and symbol filters."
    )(analyze_folded_file_impl)
    mcp.tool(
        description="Collapse perf script output into folded stacks (mapping), optionally limiting returned lines. Returns total_lines and truncated flag."
    )(collapse_perf_script_impl)
    mcp.tool(
        description="Query overhead for a symbol from a folded stack file using Trie traversal."
    )(symbol_overhead_impl)
    mcp.tool(
        description="Subset folded stacks by symbol then analyze top symbols/stacks; supports proc and symbol filters."
    )(subset_analyze_impl)
    mcp.tool(
        description="Path statistics (Trie) from folded stack file, with limit and truncated flag."
    )(path_stats_impl)


__all__ = [
    "register_flamegraph_tools",
    "analyze_folded_file_impl",
    "collapse_perf_script_impl",
    "symbol_overhead_impl",
    "subset_analyze_impl",
    "path_stats_impl",
]
