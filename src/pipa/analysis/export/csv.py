# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
from typing import Iterable, Optional

from pipa.analysis.flamegraph.analyzer import SymbolStat, StackStat


def write_symbol_stats_csv(
    path: str, stats: Iterable[SymbolStat], total: Optional[int] = None
) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if total and total > 0:
            writer.writerow(
                ["symbol", "inclusive", "inclusive_pct", "leaf", "leaf_pct"]
            )
        else:
            writer.writerow(["symbol", "inclusive", "leaf"])
        for s in stats:
            if total and total > 0:
                inc_pct = f"{(s.inclusive/total)*100:.2f}%"
                leaf_pct = f"{(s.leaf/total)*100:.2f}%"
                writer.writerow([s.symbol, s.inclusive, inc_pct, s.leaf, leaf_pct])
            else:
                writer.writerow([s.symbol, s.inclusive, s.leaf])


def write_stack_stats_csv(
    path: str, stacks: Iterable[StackStat], total: Optional[int] = None
) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if total and total > 0:
            writer.writerow(["stack", "weight", "weight_pct"])
        else:
            writer.writerow(["stack", "weight"])
        for s in stacks:
            if total and total > 0:
                weight_pct = f"{(s.weight/total)*100:.2f}%"
                writer.writerow([s.stack, s.weight, weight_pct])
            else:
                writer.writerow([s.stack, s.weight])
