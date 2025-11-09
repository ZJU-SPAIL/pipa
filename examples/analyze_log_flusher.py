# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import json
from typing import Dict

from pipa.analysis.flamegraph.io import parse_folded_file
from pipa.analysis.flamegraph.analyzer import FoldedAnalyzer, SymbolFilter
from pipa.analysis.flamegraph.trie import build_trie_from_collapsed
from pipa.analysis.export.csv import write_symbol_stats_csv, write_stack_stats_csv

ROOT = os.path.dirname(os.path.dirname(__file__))
DATA = os.path.join(ROOT, "data", "out.stacks-folded")
OUT_DIR = os.path.join(ROOT, "out", "case_log_flusher")

os.makedirs(OUT_DIR, exist_ok=True)


IO_PREFIXES = (
    "__x64_sys_",  # Linux syscalls wrapper
    "vfs_",
    "ext4_",
    "blk_",
    "submit_bio",
    "io_",
)
LOCK_PREFIXES = (
    "mutex_",
    "rwsem_",
    "spin_",
    "__lock_",
    "lock_",
)


def main() -> None:
    stacks = parse_folded_file(DATA)

    # In dataset, "log_flusher" is a symbol inside stacks (not a process name).
    subset: Dict[str, int] = {
        k: w
        for k, w in stacks.items()
        if any(part == "log_flusher" for part in k.split(";")[1:])
    }
    if not subset:
        subset = {k: w for k, w in stacks.items() if "log_flusher" in k}

    sub_an = FoldedAnalyzer.from_collapsed(subset)

    # system-call-centric hotspots on the subset
    syscall_filter = SymbolFilter(include_prefixes=IO_PREFIXES)
    io_syms = sub_an.topk_symbols(k=100, filters=syscall_filter)
    # lock-centric hotspots on the subset
    lock_filter = SymbolFilter(include_prefixes=LOCK_PREFIXES)
    lock_syms = sub_an.topk_symbols(k=100, filters=lock_filter)

    write_symbol_stats_csv(
        os.path.join(OUT_DIR, "log_flusher_io_hotspots.csv"),
        io_syms,
        total=sub_an.total_weight,
    )
    write_symbol_stats_csv(
        os.path.join(OUT_DIR, "log_flusher_lock_hotspots.csv"),
        lock_syms,
        total=sub_an.total_weight,
    )

    # Capture hot callchains related to IO and locks, within the subset
    top_stacks = sub_an.topk_stacks(2000)

    def keep_stack(sym_prefixes: tuple[str, ...], stack: str) -> bool:
        syms = stack.split(";")[1:]
        return any(any(sym.startswith(p) for p in sym_prefixes) for sym in syms)

    io_stacks = [s for s in top_stacks if keep_stack(IO_PREFIXES, s.stack)]
    lock_stacks = [s for s in top_stacks if keep_stack(LOCK_PREFIXES, s.stack)]

    write_stack_stats_csv(
        os.path.join(OUT_DIR, "log_flusher_io_stacks.csv"),
        io_stacks,
        total=sub_an.total_weight,
    )
    write_stack_stats_csv(
        os.path.join(OUT_DIR, "log_flusher_lock_stacks.csv"),
        lock_stacks,
        total=sub_an.total_weight,
    )

    # ---- Trie-based: path stats and sorted subtrees for log_flusher ----
    if subset:
        trie = build_trie_from_collapsed(subset)
        path_stats_csv = os.path.join(OUT_DIR, "log_flusher_trie_path_stats.csv")
        with open(path_stats_csv, "w", encoding="utf-8") as f:
            f.write("path,count,percent\n")
            for path, cnt, pct in trie.to_path_stats():
                f.write(f"{path},{cnt},{pct:.2f}%\n")
        # pick a symbol to expand: prefer 'log_flusher' itself if present
        subtree = trie.export_sorted_tree(start_symbol="log_flusher", fuzzy=True, k=3)
        with open(
            os.path.join(OUT_DIR, "log_flusher_trie_subtree.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(subtree, f, ensure_ascii=False, indent=2)

        # ---- Heuristics for potential redundant flush/syscalls ----
        # 1) k-depth overhead around fsync/fdatasync
        q_fsync = trie.query_symbol_overhead("fsync", k=2, fuzzy=True)
        q_fdatasync = trie.query_symbol_overhead("fdatasync", k=2, fuzzy=True)
        # 2) Co-occurrence in same callchains and their total weights
        total = sum(subset.values()) or 1
        weight_fsync = 0
        weight_fdatasync = 0
        weight_both = 0
        for key, w in subset.items():
            syms = key.split(";")[1:]
            has_fsync = any("fsync" in s for s in syms)
            has_fdatasync = any("fdatasync" in s for s in syms)
            if has_fsync:
                weight_fsync += w
            if has_fdatasync:
                weight_fdatasync += w
            if has_fsync and has_fdatasync:
                weight_both += w
        summary = {
            "total_weight": total,
            "fsync_k2_overhead": q_fsync,
            "fdatasync_k2_overhead": q_fdatasync,
            "weight_fsync_paths": weight_fsync,
            "weight_fdatasync_paths": weight_fdatasync,
            "weight_both_paths": weight_both,
            "weight_fsync_pct": round(weight_fsync * 100.0 / total, 2),
            "weight_fdatasync_pct": round(weight_fdatasync * 100.0 / total, 2),
            "weight_both_pct": round(weight_both * 100.0 / total, 2),
        }
        with open(
            os.path.join(OUT_DIR, "log_flusher_fsync_summary.json"),
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
