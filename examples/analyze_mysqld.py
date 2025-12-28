# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import re
import json
from typing import List

from pipa.analysis.flamegraph.io import parse_folded_file
from pipa.analysis.flamegraph.analyzer import FoldedAnalyzer, SymbolFilter
from pipa.analysis.flamegraph.trie import build_trie_from_collapsed
from pipa.analysis.flamegraph.csv_export import write_symbol_stats_csv, write_stack_stats_csv

ROOT = os.path.dirname(os.path.dirname(__file__))
DATA = os.path.join(ROOT, "data", "out.stacks-folded")
OUT_DIR = os.path.join(ROOT, "out", "case_mysqld")

os.makedirs(OUT_DIR, exist_ok=True)


def pick_hot_callchains(an: FoldedAnalyzer, k: int = 50) -> List[str]:
    top = an.topk_stacks(k)
    return [s.stack for s in top]


def main() -> None:
    stacks = parse_folded_file(DATA)
    an = FoldedAnalyzer.from_collapsed(stacks)

    # 1) Limit to mysqld process via regex
    proc_re = re.compile(r"^mysqld(\b|\s|$)")

    # Hot symbols (inclusive)
    hot_syms = an.topk_symbols(k=50, proc_regex=proc_re)
    write_symbol_stats_csv(
        os.path.join(OUT_DIR, "mysqld_hot_symbols.csv"), hot_syms, total=an.total_weight
    )

    # Hot stacks (callchains)
    hot_stacks = an.topk_stacks(k=100)
    # Filter stacks by process regex manually
    hot_stacks = [s for s in hot_stacks if proc_re.search(s.stack.split(";")[0])]
    write_stack_stats_csv(
        os.path.join(OUT_DIR, "mysqld_hot_stacks.csv"),
        hot_stacks,
        total=an.total_weight,
    )

    # Optionally: focus on common MySQL hotspots (io/lock related prefixes)
    filt = SymbolFilter(include_prefixes=("lock_", "buf_", "row_", "trx_", "fil_"))
    hot_syms_focus = an.topk_symbols(k=50, proc_regex=proc_re, filters=filt)
    write_symbol_stats_csv(
        os.path.join(OUT_DIR, "mysqld_hot_symbols_focus.csv"),
        hot_syms_focus,
        total=an.total_weight,
    )

    # Save top callchains text for inspection
    with open(
        os.path.join(OUT_DIR, "mysqld_hot_callchains.txt"), "w", encoding="utf-8"
    ) as f:
        for line in pick_hot_callchains(an, 200):
            if proc_re.search(line.split(";")[0]):
                f.write(line + "\n")

    # ---- Trie-based: path stats and sorted subtrees ----
    trie = build_trie_from_collapsed(stacks)

    # Export top path stats (call chains without process label), as CSV
    path_stats_csv = os.path.join(OUT_DIR, "mysqld_trie_path_stats.csv")
    with open(path_stats_csv, "w", encoding="utf-8") as f:
        f.write("path,count,percent\n")
        for path, cnt, pct in trie.to_path_stats():
            # 只保留 mysqld 相关：检查任一原始栈首段是否匹配
            # 这里简单用路径层面无法识别进程，直接全量导出，便于后续筛选
            f.write(f"{path},{cnt},{pct:.2f}%\n")

    # Export a sorted subtree starting at a hot symbol (if any)
    if hot_syms:
        hot_sym = hot_syms[0].symbol
        subtree = trie.export_sorted_tree(start_symbol=hot_sym, fuzzy=False, k=3)
        with open(
            os.path.join(OUT_DIR, "mysqld_trie_subtree.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(subtree, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
