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
    We also skip perf-script metadata or counters that do not resemble folded stacks.
    Heuristics to skip:
    - Lines whose key starts with '#' or ':' (metadata/counters)
    - Lines whose key does not contain ';' (no stack delimiter)
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
        # Normalize key
        key = key.strip()
        if not key:
            continue
        # Skip metadata/counter lines
        if key.startswith("#") or key.startswith(":"):
            continue
        # Require at least one ';' to ensure there is a process and at least one frame
        if ";" not in key:
            continue
        stacks[key] = stacks.get(key, 0) + weight
    return stacks


def parse_folded_file(path: str) -> Dict[str, int]:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return parse_folded_lines(f)
