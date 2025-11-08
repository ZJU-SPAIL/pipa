# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import (
    Dict,
    Iterable,
    List,
    Tuple,
    Optional,
    Callable,
    Mapping,
    Pattern,
    Sequence,
)
import re

Separator = ";"


@dataclass(frozen=True)
class SymbolStat:
    symbol: str
    inclusive: int
    leaf: int

    @property
    def total(self) -> int:
        return self.inclusive


@dataclass(frozen=True)
class StackStat:
    stack: str
    weight: int


@dataclass(frozen=True)
class DSOStat:
    dso: str
    inclusive: int
    leaf: int


# Enriched value objects that carry percentage members
@dataclass(frozen=True)
class SymbolShare:
    symbol: str
    inclusive: int
    leaf: int
    inclusive_pct: float  # percentage in [0,100]
    leaf_pct: float       # percentage in [0,100]


@dataclass(frozen=True)
class StackShare:
    stack: str
    weight: int
    weight_pct: float  # percentage in [0,100]


@dataclass(frozen=True)
class SymbolFilter:
    include_prefixes: Tuple[str, ...] = ()
    include_suffixes: Tuple[str, ...] = ()
    exclude_prefixes: Tuple[str, ...] = ()
    exclude_suffixes: Tuple[str, ...] = ()

    def matches(self, symbol: str) -> bool:
        if self.include_prefixes or self.include_suffixes:
            ok = False
            if self.include_prefixes and any(
                symbol.startswith(p) for p in self.include_prefixes
            ):
                ok = True
            if self.include_suffixes and any(
                symbol.endswith(s) for s in self.include_suffixes
            ):
                ok = True
            if not ok:
                return False
        if self.exclude_prefixes and any(
            symbol.startswith(p) for p in self.exclude_prefixes
        ):
            return False
        if self.exclude_suffixes and any(
            symbol.endswith(s) for s in self.exclude_suffixes
        ):
            return False
        return True


class FoldedAnalyzer:
    def __init__(self, stacks: Dict[str, int]) -> None:
        self._stacks: Dict[str, int] = dict(stacks)
        self._total_weight: int = sum(self._stacks.values())

    @classmethod
    def from_collapsed(cls, collapsed: Mapping[str, int]) -> "FoldedAnalyzer":
        return cls(dict(collapsed))

    @property
    def total_weight(self) -> int:
        return self._total_weight

    def iter_items(self) -> Iterable[Tuple[str, int]]:
        return self._stacks.items()

    def topk_stacks(
        self, k: int = 20, key: Optional[Callable[[Tuple[str, int]], int]] = None
    ) -> List[StackStat]:
        if k <= 0:
            return []
        items = list(self._stacks.items())
        if key is None:
            items.sort(key=lambda kv: kv[1], reverse=True)
        else:
            items.sort(key=key, reverse=True)  # type: ignore[arg-type]
        return [StackStat(stack=s, weight=w) for s, w in items[:k]]

    def _accumulate_symbol_costs(
        self,
        proc_prefix: Optional[str] = None,
        proc_regex: Optional[Pattern[str]] = None,
        filters: Optional[SymbolFilter] = None,
    ) -> Dict[str, Tuple[int, int]]:
        acc: Dict[str, Tuple[int, int]] = {}
        for stack, weight in self._stacks.items():
            frames = stack.split(Separator)
            if not frames:
                continue
            proc = frames[0]
            if proc_prefix is not None and not proc.startswith(proc_prefix):
                continue
            if proc_regex is not None and re.search(proc_regex, proc) is None:
                continue
            syms = frames[1:]
            for sym in syms:
                if filters and not filters.matches(sym):
                    continue
                inc, leaf = acc.get(sym, (0, 0))
                inc += weight
                acc[sym] = (inc, leaf)
            if syms:
                leaf_sym = syms[-1]
                if not filters or filters.matches(leaf_sym):
                    inc, leaf = acc.get(leaf_sym, (0, 0))
                    leaf += weight
                    acc[leaf_sym] = (inc, leaf)
        return acc

    def symbol_hotspots(
        self,
        proc_prefix: Optional[str] = None,
        proc_regex: Optional[Pattern[str]] = None,
        filters: Optional[SymbolFilter] = None,
    ) -> List[SymbolStat]:
        acc = self._accumulate_symbol_costs(proc_prefix, proc_regex, filters)
        stats = [
            SymbolStat(symbol=s, inclusive=inc, leaf=leaf)
            for s, (inc, leaf) in acc.items()
        ]
        stats.sort(key=lambda x: (x.inclusive, x.leaf), reverse=True)
        return stats

    def topk_symbols(
        self,
        k: int = 20,
        proc_prefix: Optional[str] = None,
        by: str = "inclusive",
        proc_regex: Optional[Pattern[str]] = None,
        filters: Optional[SymbolFilter] = None,
    ) -> List[SymbolStat]:
        stats = self.symbol_hotspots(proc_prefix, proc_regex, filters)
        if by == "leaf":
            stats.sort(key=lambda x: x.leaf, reverse=True)
        else:
            stats.sort(key=lambda x: x.inclusive, reverse=True)
        return stats[:k]

    def symbol_share(
        self,
        symbol: str,
        proc_prefix: Optional[str] = None,
        by: str = "inclusive",
        proc_regex: Optional[Pattern[str]] = None,
        filters: Optional[SymbolFilter] = None,
    ) -> float:
        if self._total_weight == 0:
            return 0.0
        stats = {
            s.symbol: s for s in self.symbol_hotspots(proc_prefix, proc_regex, filters)
        }
        if symbol not in stats:
            return 0.0
        val = stats[symbol].leaf if by == "leaf" else stats[symbol].inclusive
        return float(val) / float(self._total_weight)

    def children_hotspots(
        self,
        parent_symbol: str,
        proc_prefix: Optional[str] = None,
        proc_regex: Optional[Pattern[str]] = None,
        filters: Optional[SymbolFilter] = None,
    ) -> List[SymbolStat]:
        acc: Dict[str, Tuple[int, int]] = {}
        for stack, weight in self._stacks.items():
            frames = stack.split(Separator)
            if not frames or len(frames) < 3:
                continue
            proc = frames[0]
            if proc_prefix is not None and not proc.startswith(proc_prefix):
                continue
            if proc_regex is not None and re.search(proc_regex, proc) is None:
                continue
            syms = frames[1:]
            for i in range(len(syms) - 1):
                if syms[i] != parent_symbol:
                    continue
                child = syms[i + 1]
                if filters and not filters.matches(child):
                    continue
                inc, leaf = acc.get(child, (0, 0))
                inc += weight
                if i + 1 == len(syms) - 1:
                    leaf += weight
                acc[child] = (inc, leaf)
        stats = [
            SymbolStat(symbol=s, inclusive=inc, leaf=leaf)
            for s, (inc, leaf) in acc.items()
        ]
        stats.sort(key=lambda x: (x.inclusive, x.leaf), reverse=True)
        return stats

    # Subset helpers
    def _subset_by_predicate(
        self, pred: Callable[[List[str]], bool]
    ) -> "FoldedAnalyzer":
        subset: Dict[str, int] = {}
        for stack, weight in self._stacks.items():
            frames = stack.split(Separator)
            if len(frames) < 2:
                continue
            syms = frames[1:]
            if pred(syms):
                subset[stack] = subset.get(stack, 0) + weight
        return FoldedAnalyzer(subset)

    def subset_by_path_prefix(self, prefix: Sequence[str]) -> "FoldedAnalyzer":
        prefix = tuple(prefix)
        return self._subset_by_predicate(
            lambda syms: len(syms) >= len(prefix)
            and syms[: len(prefix)] == list(prefix)
        )

    def subset_by_path_suffix(self, suffix: Sequence[str]) -> "FoldedAnalyzer":
        suffix = tuple(suffix)
        return self._subset_by_predicate(
            lambda syms: len(syms) >= len(suffix)
            and syms[-len(suffix) :] == list(suffix)
        )

    def subset_by_symbol(
        self, symbol: str, contains_fallback: bool = True
    ) -> "FoldedAnalyzer":
        subset: Dict[str, int] = {}
        for stack, weight in self._stacks.items():
            frames = stack.split(Separator)
            if len(frames) < 2:
                continue
            syms = frames[1:]
            if symbol in syms:
                subset[stack] = subset.get(stack, 0) + weight
            elif contains_fallback and symbol in stack:
                subset[stack] = subset.get(stack, 0) + weight
        return FoldedAnalyzer(subset)

    def filter_stacks_by_prefixes(
        self, prefixes: Sequence[str], k: int = 1000
    ) -> List[StackStat]:
        top = self.topk_stacks(k)

        def keep(stack: str) -> bool:
            syms = stack.split(Separator)[1:]
            for p in prefixes:
                if any(s.startswith(p) for s in syms):
                    return True
            return False

        return [s for s in top if keep(s.stack)]

    # ---------- Percentage helpers (non-breaking) ----------
    def to_symbol_shares(
        self, stats: Iterable[SymbolStat], total: Optional[int] = None
    ) -> List[SymbolShare]:
        denom = total if total is not None else self._total_weight
        if denom <= 0:
            denom = 1
        shares: List[SymbolShare] = []
        for s in stats:
            shares.append(
                SymbolShare(
                    symbol=s.symbol,
                    inclusive=s.inclusive,
                    leaf=s.leaf,
                    inclusive_pct=(s.inclusive / denom) * 100.0,
                    leaf_pct=(s.leaf / denom) * 100.0,
                )
            )
        return shares

    def to_stack_shares(
        self, stacks: Iterable[StackStat], total: Optional[int] = None
    ) -> List[StackShare]:
        denom = total if total is not None else self._total_weight
        if denom <= 0:
            denom = 1
        shares: List[StackShare] = []
        for s in stacks:
            shares.append(
                StackShare(
                    stack=s.stack,
                    weight=s.weight,
                    weight_pct=(s.weight / denom) * 100.0,
                )
            )
        return shares
