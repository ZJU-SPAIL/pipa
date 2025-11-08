# -*- coding: utf-8 -*-
"""
IO helpers for folded stacks.

This module focuses on parsing and serializing the folded stacks text format:
- Each line: "proc;f1;f2;...;fn <weight>"
- Left part is a semicolon-separated stack key
- Right part is an integer weight

We do not depend on collapse implementation details. We only accept and return
plain mappings for maximum reuse.
"""
from __future__ import annotations

from typing import Dict, Iterable


def parse_folded_lines(lines: Iterable[str]) -> Dict[str, int]:
    """Parse folded stacks lines into a mapping.

    Lines that are empty or malformed are ignored safely.
    """
    stacks: Dict[str, int] = {}
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        # Split by last space to tolerate spaces inside symbols (if any)
        try:
            key, weight_str = line.rsplit(" ", 1)
            weight = int(weight_str)
        except ValueError:
            # Malformed line: ignore
            continue
        # Normalize key: strip trailing/leading spaces
        key = key.strip()
        if not key:
            continue
        stacks[key] = stacks.get(key, 0) + weight
    return stacks


def parse_folded_file(path: str) -> Dict[str, int]:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return parse_folded_lines(f)
