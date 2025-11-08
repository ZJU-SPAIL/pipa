# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
from typing import Iterable

from pipa.analysis.flamegraph.analyzer import SymbolStat, StackStat


def write_symbol_stats_csv(path: str, stats: Iterable[SymbolStat]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["symbol", "inclusive", "leaf"])
        for s in stats:
            writer.writerow([s.symbol, s.inclusive, s.leaf])


def write_stack_stats_csv(path: str, stacks: Iterable[StackStat]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["stack", "weight"])
        for s in stacks:
            writer.writerow([s.stack, s.weight])
