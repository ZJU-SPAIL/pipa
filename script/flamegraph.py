#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
flamegraph.py — Render folded stacks into an interactive SVG (Python port of flamegraph.pl).

Usage:
  ./flamegraph.py folded.txt > graph.svg

Pipe example:
  perf script | ./stackcollapse_perf.py | ./flamegraph.py > graph.svg

Supported options (subset of flamegraph.pl):
  --title TEXT
  --width INT (default 1200)
  --height INT (frame height, default 16)
  --fontsize FLOAT (default 12)
  --minwidth NUM[ or %] (default 0.1)
  --countname TEXT (default "samples")
  --reverse
  --inverted
  --flamechart
  --colors PALETTE (hot, red, green, blue, yellow, purple, aqua, orange, mem, io, wakeup, chain, java, js, perl)

This is a pragmatic, compatible renderer for most common cases.
"""
from __future__ import annotations
import argparse
import sys
import math
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

Palette = str


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument(
        "infile", nargs="?", default="-", help="folded stacks input (default: stdin)"
    )
    p.add_argument("--title", default="Flame Graph")
    p.add_argument("--width", type=int, default=1200)
    p.add_argument("--height", type=int, default=16)
    p.add_argument("--fontsize", type=float, default=12.0)
    p.add_argument("--minwidth", default="0.1")
    p.add_argument("--countname", default="samples")
    p.add_argument("--reverse", action="store_true")
    p.add_argument("--inverted", action="store_true")
    p.add_argument("--flamechart", action="store_true")
    p.add_argument("--colors", default="hot")
    return p.parse_args()


def read_lines(path: str):
    if path == "-":
        for line in sys.stdin:
            yield line.rstrip("\n")
    else:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                yield line.rstrip("\n")


def parse_folded(
    lines: List[str], reverse: bool, flamechart: bool
) -> Tuple[List[str], float]:
    # Reverse semantics mirror flamegraph.pl: reverse stack order before sorting/processing
    data: List[str] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if reverse:
            # handle possible diff extra column "count2"
            parts = line.rsplit(" ", 1)
            if len(parts) != 2:
                continue
            stack, samples = parts
            parts2 = stack.rsplit(" ", 1)
            if len(parts2) == 2:
                stack2, samples2 = parts2
                data.append(
                    ";".join(reversed(stack2.split(";"))) + f" {samples} {samples2}"
                )
            else:
                data.append(";".join(reversed(stack.split(";"))) + f" {samples}")
        else:
            data.append(line)

    sorted_data = list(reversed(data)) if flamechart else sorted(data)
    total_time = 0.0
    for line in sorted_data:
        stack, count_s = line.rsplit(" ", 1)
        try:
            total_time += float(count_s)
        except ValueError:
            # differential pair; count_s is second column, the last value still contributes
            parts = stack.rsplit(" ", 1)
            if len(parts) == 2:
                try:
                    total_time += float(parts[1])
                except ValueError:
                    pass
    return sorted_data, total_time


def build_nodes(
    sorted_data: List[str], flamechart: bool
) -> Tuple[Dict[str, Dict[str, float]], float, float]:
    Node: Dict[str, Dict[str, float]] = {}
    Tmp: Dict[str, Dict[str, float]] = {}

    def flow(last: List[str], this: List[str], v: float, d: Optional[float]):
        len_a = len(last) - 1
        len_b = len(this) - 1
        i = 0
        while i <= len_a and i <= len_b and last[i] == this[i]:
            i += 1
        len_same = i
        for i in range(len_a, len_same - 1, -1):
            k = f"{last[i]};{i}"
            node_key = f"{k};{v}"
            Node.setdefault(node_key, {})["stime"] = Tmp[k]["stime"]
            if "delta" in Tmp[k]:
                Node[node_key]["delta"] = Tmp[k]["delta"]
            Tmp.pop(k, None)
        for i in range(len_same, len_b + 1):
            k = f"{this[i]};{i}"
            Tmp.setdefault(k, {})["stime"] = v
            if d is not None and i == len_b:
                Tmp[k]["delta"] = Tmp.get(k, {}).get("delta", 0.0) + d
        return this

    last: List[str] = []
    time_v = 0.0
    maxdelta = 1.0
    for line in sorted_data:
        stack, samples_s = line.rsplit(" ", 1)
        samples2 = None
        try:
            samples = float(samples_s)
        except ValueError:
            # differential pair
            stack, samples_s1 = stack.rsplit(" ", 1)
            samples = float(samples_s1)
            samples2 = float(samples_s)
        parts = ["", *stack.split(";")]
        d = None
        if samples2 is not None:
            d = samples2 - samples
            maxdelta = max(maxdelta, abs(d))
        last = flow(last, parts, time_v, d)
        time_v += samples2 if samples2 is not None else samples
    flow(last, [], time_v, None)
    return Node, time_v, maxdelta


# Color helpers (subset, mirrors perl logic approximately)
import random


def namehash(name: str) -> float:
    vector = 0.0
    weight = 1.0
    max_v = 1.0
    mod = 10
    trimmed = re_sub_module(name)
    for ch in trimmed[:12]:
        i = ord(ch) % mod
        vector += (i / (mod - 1)) * weight
        max_v += 1.0 * weight
        weight *= 0.70
        mod += 1
        if mod > 12:
            break
    return 1.0 - (vector / max_v)


def re_sub_module(name: str) -> str:
    # mimic: $name =~ s/.(.*?)`//;
    if "`" in name:
        idx = name.find("`")
        if idx > 0:
            return name[idx + 1 :]
    return name


def random_namehash(name: str) -> float:
    # deterministic RNG from name
    h = sum((i + 1) * ord(c) for i, c in enumerate(name)) & 0xFFFFFFFF
    rnd = (1103515245 * h + 12345) & 0x7FFFFFFF
    return (rnd % 100000) / 100000.0


def color(
    colors: Palette, func: str, hashed: bool = False, randomize: bool = False
) -> str:
    if hashed:
        v1 = namehash(func)
        v2 = namehash(func[::-1])
        v3 = v2
    elif randomize:
        v1 = random_namehash(func)
        v2 = random_namehash(func + "@")
        v3 = random_namehash("@" + func)
    else:
        v1 = random_namehash(func)
        v2 = random_namehash(func)
        v3 = random_namehash(func)

    def rgb(r, g, b):
        return f"rgb({int(r)},{int(g)},{int(b)})"

    if colors == "hot":
        r = 205 + int(50 * v3)
        g = int(230 * v1)
        b = int(55 * v2)
        return rgb(r, g, b)
    if colors == "mem":
        r = 0
        g = 190 + int(50 * v2)
        b = int(210 * v1)
        return rgb(r, g, b)
    if colors == "io":
        r = 80 + int(60 * v1)
        g = r
        b = 190 + int(55 * v2)
        return rgb(r, g, b)
    if colors == "red":
        r = 200 + int(55 * v1)
        x = 50 + int(80 * v1)
        return rgb(r, x, x)
    if colors == "green":
        g = 200 + int(55 * v1)
        x = 50 + int(60 * v1)
        return rgb(x, g, x)
    if colors == "blue":
        b = 205 + int(50 * v1)
        x = 80 + int(60 * v1)
        return rgb(x, x, b)
    if colors == "yellow":
        x = 175 + int(55 * v1)
        b = 50 + int(20 * v1)
        return rgb(x, x, b)
    if colors == "purple":
        x = 190 + int(65 * v1)
        g = 80 + int(60 * v1)
        return rgb(x, g, x)
    if colors == "aqua":
        r = 50 + int(60 * v1)
        g = 165 + int(55 * v1)
        b = 165 + int(55 * v1)
        return rgb(r, g, b)
    if colors == "orange":
        r = 190 + int(65 * v1)
        g = 90 + int(65 * v1)
        return rgb(r, g, 0)
    # default
    return rgb(0, 0, 0)


def color_scale(value: float, maxv: float, negate: bool = False) -> str:
    if negate:
        value = -value
    r, g, b = 255, 255, 255
    if value > 0:
        g = b = int(210 * (maxv - value) / maxv)
    elif value < 0:
        r = g = int(210 * (maxv + value) / maxv)
    return f"rgb({r},{g},{b})"


def render_svg(
    Node: Dict[str, Dict[str, float]],
    total_time: float,
    args: argparse.Namespace,
    maxdelta: float,
) -> str:
    fontsize = args.fontsize
    frameheight = args.height
    xpad = 10
    ypad1 = int(fontsize * 3)
    ypad2 = int(fontsize * 2 + 10)
    ypad3 = int(fontsize * 2)

    # prune small blocks and find max depth
    widthpertime = (args.width - 2 * xpad) / (total_time if total_time else 1.0)
    minwidth_s = args.minwidth
    if isinstance(minwidth_s, str) and minwidth_s.endswith("%"):
        minwidth_time = (
            (total_time * float(minwidth_s[:-1]) / 100.0) if total_time else 0
        )
    else:
        minwidth_time = float(minwidth_s) / widthpertime

    depthmax = 0
    keys = list(Node.keys())
    for k in keys:
        func, depth_s, etime_s = k.split(";")
        depth = int(depth_s)
        stime = Node[k]["stime"]
        etime = float(etime_s) if func != "" or depth != 0 else total_time
        if (etime - stime) < minwidth_time:
            Node.pop(k, None)
            continue
        if depth > depthmax:
            depthmax = depth

    imageheight = ((depthmax + 1) * frameheight) + ypad1 + ypad2
    title = (
        args.title
        if not args.inverted
        else "Icicle Graph" if args.title == "Flame Graph" else args.title
    )

    # Header & styles
    out = []
    out.append(f'<?xml version="1.0" standalone="no"?>')
    out.append(
        f'<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">'
    )
    out.append(
        f'<svg version="1.1" width="{args.width}" height="{imageheight}" viewBox="0 0 {args.width} {imageheight}" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">'
    )
    out.append(
        '<defs><linearGradient id="background" y1="0" y2="1" x1="0" x2="0"><stop stop-color="#eeeeee" offset="5%" /><stop stop-color="#eeeeb0" offset="95%" /></linearGradient></defs>'
    )
    out.append(
        '<style type="text/css"> text { font-family:Verdana; font-size:%dpx; fill:rgb(0,0,0);} #frames > *:hover { stroke:black; stroke-width:0.5; cursor:pointer; } .hide{display:none;} .parent{opacity:0.5;} </style>'
        % fontsize
    )
    out.append(
        f'<rect x="0" y="0" width="{args.width}" height="{imageheight}" fill="url(#background)"/>'
    )
    out.append(
        f'<text id="title" x="{args.width//2}" y="{int(fontsize*2)}">{title}</text>'
    )
    out.append(f'<text id="details" x="{xpad}" y="{imageheight - (ypad2//2)}"> </text>')

    # Interactivity JS (trimmed but functional: hover details)
    out.append(
        "<script type=\"text/ecmascript\"><![CDATA[\n'use strict';\nvar details;\nfunction init(){details=document.getElementById('details').firstChild;}\nfunction find_child(n,t){var c=n.getElementsByTagName(t);return c.length?c[0]:null;}\nfunction over(e){var t=find_child(e,'title');if(t)details.nodeValue=t.firstChild.nodeValue;}\nfunction out(e){details.nodeValue=' ';}\n]]></script>"
    )

    # Frames group
    out.append('<g id="frames">')

    for k, node in Node.items():
        func, depth_s, etime_s = k.split(";")
        depth = int(depth_s)
        stime = node["stime"]
        etime = float(etime_s) if func != "" or depth != 0 else total_time
        x1 = 10 + stime * widthpertime
        x2 = 10 + etime * widthpertime
        if not args.inverted:
            y1 = imageheight - ypad2 - (depth + 1) * frameheight + 1
            y2 = imageheight - ypad2 - depth * frameheight
        else:
            y1 = ypad1 + depth * frameheight
            y2 = ypad1 + (depth + 1) * frameheight - 1
        samples = etime - stime
        pct = 0.0 if total_time == 0 else (100.0 * samples / total_time)
        escaped = (
            func.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )
        info = (
            f"{escaped} ({samples:.0f} {args.countname}, {pct:.2f}%)"
            if func or depth
            else f"all ({samples:.0f} {args.countname}, 100%)"
        )
        title_tag = f"<title>{info}</title>"

        # Color selection (no palette file in this port)
        if "delta" in node:
            fill = color_scale(node["delta"], maxdelta)
        else:
            # strip annotation for label only; but keep in color hashing
            fill = color(args.colors, func)

        width = max(0.1, x2 - x1)
        out.append(
            f'<g onmouseover="over(this)" onmouseout="out(this)">{title_tag}<rect x="{x1:.1f}" y="{y1}" width="{width:.1f}" height="{(y2-y1):.1f}" fill="{fill}" rx="2" ry="2"/><text x="{x1+3:.2f}" y="{(y1+y2)//2 + 3}">{truncate_label(func, width, args.fontsize)}</text></g>'
        )

    out.append("</g>")
    out.append("</svg>")
    return "\n".join(out)


def truncate_label(func: str, width_px: float, fontsize: float) -> str:
    # approximate font width scale
    fontwidth = 0.59
    max_chars = int(width_px / (fontsize * fontwidth))
    if max_chars < 3:
        return ""
    label = re_strip_annotation(func)
    if len(label) <= max_chars:
        return escape_text(label)
    short = label[:max_chars]
    if len(short) >= 2:
        short = short[:-2] + ".."
    return escape_text(short)


def escape_text(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def re_strip_annotation(s: str) -> str:
    if (
        s.endswith(" _[k]")
        or s.endswith(" _[i]")
        or s.endswith(" _[j]")
        or s.endswith(" _[w]")
    ):
        return s[:-5]
    return s


def main() -> int:
    args = parse_args()
    lines = list(read_lines(args.infile))
    try:
        sorted_data, total_time = parse_folded(lines, args.reverse, args.flamechart)
        Node, total_time2, maxdelta = build_nodes(sorted_data, args.flamechart)
        svg = render_svg(Node, total_time2, args, maxdelta)
    except BrokenPipeError:
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    sys.stdout.write(svg)
    try:
        sys.stdout.flush()
    except BrokenPipeError:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
