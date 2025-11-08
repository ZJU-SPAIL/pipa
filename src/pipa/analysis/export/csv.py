# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
from typing import Iterable, Optional, Union

from pipa.analysis.flamegraph.analyzer import (
    SymbolStat,
    StackStat,
    SymbolShare,
    StackShare,
)


# The CSV writers accept either raw stats or enriched shares.
# If enriched shares are provided, percentage columns are written directly.
# Otherwise, if a total is provided, percentages are computed on the fly for backward compatibility.

def write_symbol_stats_csv(
    path: str, stats: Iterable[Union[SymbolStat, SymbolShare]], total: Optional[int] = None
) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        first = None
        for first in stats:
            break
        # Recreate iterator: if we consumed one, we need to write it back.
        if first is None:
            # empty input
            writer.writerow(["symbol", "inclusive", "leaf"]) if not total else writer.writerow([
                "symbol",
                "inclusive",
                "inclusive_pct",
                "leaf",
                "leaf_pct",
            ])
            return
        # Determine mode by instance type
        is_share = isinstance(first, SymbolShare)
        # Write header
        if is_share:
            writer.writerow(["symbol", "inclusive", "inclusive_pct", "leaf", "leaf_pct"])
        elif total and total > 0:
            writer.writerow(["symbol", "inclusive", "inclusive_pct", "leaf", "leaf_pct"])
        else:
            writer.writerow(["symbol", "inclusive", "leaf"])
        # Write first row then the rest
        def write_row(s):
            if is_share:
                writer.writerow([
                    s.symbol,
                    s.inclusive,
                    f"{s.inclusive_pct:.2f}%",
                    s.leaf,
                    f"{s.leaf_pct:.2f}%",
                ])
            elif total and total > 0:
                inc_pct = (s.inclusive / total) * 100.0
                leaf_pct = (s.leaf / total) * 100.0
                writer.writerow([
                    s.symbol,
                    s.inclusive,
                    f"{inc_pct:.2f}%",
                    s.leaf,
                    f"{leaf_pct:.2f}%",
                ])
            else:
                writer.writerow([s.symbol, s.inclusive, s.leaf])
        write_row(first)
        for s in stats:
            write_row(s)


def write_stack_stats_csv(
    path: str, stacks: Iterable[Union[StackStat, StackShare]], total: Optional[int] = None
) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        first = None
        for first in stacks:
            break
        if first is None:
            writer.writerow(["stack", "weight"]) if not total else writer.writerow([
                "stack",
                "weight",
                "weight_pct",
            ])
            return
        is_share = isinstance(first, StackShare)
        if is_share:
            writer.writerow(["stack", "weight", "weight_pct"])
        elif total and total > 0:
            writer.writerow(["stack", "weight", "weight_pct"])
        else:
            writer.writerow(["stack", "weight"])
        def write_row(s):
            if is_share:
                writer.writerow([s.stack, s.weight, f"{s.weight_pct:.2f}%"])
            elif total and total > 0:
                weight_pct = (s.weight / total) * 100.0
                writer.writerow([s.stack, s.weight, f"{weight_pct:.2f}%"])
            else:
                writer.writerow([s.stack, s.weight])
        write_row(first)
        for s in stacks:
            write_row(s)
