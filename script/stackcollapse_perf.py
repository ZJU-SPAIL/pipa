#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
stackcollapse_perf.py — 将 `perf script` 的调用栈折叠为单行（folded stacks）。

用途:
  - 从标准输入读取:
      perf script | ./stackcollapse_perf.py > out.stacks-folded
  - 从文件读取:
      ./stackcollapse_perf.py input.txt > out.stacks-folded

选项:
  --pid                在进程名后附加 PID
  --tid                在进程名后附加 PID/TID
  --kernel             为内核栈帧追加后缀 _[k]
  --jit                为 JIT 栈帧追加后缀 _[j]
  --all                同时启用内核与 JIT 标注
  --addrs              当无符号时保留原始地址
  --event-filter NAME  仅保留事件名等于 NAME 的样本
  --inline             尝试用 addr2line 做内联展开（尽力而为）
  --context            搭配 --inline，包含源位置（file:line）
  --srcline            解析 perf -F+srcline 并将源位置信息并入符号

说明:
  - perf script 的输出格式可能存在差异；解析器使用更宽松的正则与启发式以提升鲁棒性。
  - 结果为“进程;帧1;帧2;... 采样权重”的折叠行，可直接供火焰图工具使用。
"""
from __future__ import annotations
import argparse
import os
import re
import sys
import subprocess
from collections import defaultdict
from typing import Dict, List, Optional, Tuple


# 头部行（样本记录起始）的前半段：捕获进程名、PID、可选的 TID
HEADER_PERL_HEAD_RE = re.compile(r"^\s*(\S.+?)\s+(\d+)(?:/(\d+))?\s+", re.ASCII)
# 头部行的后半段：捕获可选的周期(period)与事件名(event)
HEADER_PERL_TAIL_RE = re.compile(r":\s*(\d+)?\s+(\S+):\s*$")
# 仅以冒号结尾的头部行（无显示周期/事件）
HEADER_ONLY_COLON_LINE_RE = re.compile(r"^\s*(.+?):\s*$")
# 栈帧行（包含指令地址 ip、符号、模块），宽松匹配，尽量兼容多种格式
FRAME_RE = re.compile(r"^\s*([0-9A-Fa-fx]+)\s*(.+) \((.*)\)\s*$")
# 无 ip 的栈帧行（仅符号与模块）
FRAME_NOIP_RE = re.compile(r"^\s*(.+) \((.*)\)\s*$")

# 从符号中剥离地址偏移（+0x...）
ADDR_OFFSET_RE = re.compile(r"^(.+)\+0x([0-9a-fA-F]+)$")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument(
        "infile", nargs="?", default="-", help="perf script output (default: stdin)"
    )
    p.add_argument("--pid", action="store_true", dest="include_pid")
    p.add_argument("--tid", action="store_true", dest="include_tid")
    p.add_argument("--kernel", action="store_true")
    p.add_argument("--jit", action="store_true")
    p.add_argument("--all", action="store_true", dest="annotate_all")
    p.add_argument("--addrs", action="store_true")
    p.add_argument("--event-filter", dest="event_filter", default="")
    p.add_argument("--inline", action="store_true", dest="do_inline")
    p.add_argument("--context", action="store_true")
    p.add_argument("--srcline", action="store_true")
    return p.parse_args()


def is_kernel_dso_perl_like(dso: str) -> bool:
    # 逻辑：模块名以 "[" 开头或以 "vmlinux" 结尾，且不包含 "unknown"，视为内核模块
    if not dso:
        return False
    if "unknown" in dso:
        return False
    return dso.startswith("[") or dso.endswith("vmlinux")


def is_jit_dso_perl_like(dso: str) -> bool:
    # 逻辑：路径形如 /tmp/perf-<pid>.map 的模块视为 JIT 映射
    if not dso:
        return False
    return re.search(r"/tmp/perf-\d+\.map", dso) is not None


def strip_addr_offset(sym: str) -> str:
    m = ADDR_OFFSET_RE.match(sym)
    if m:
        return m.group(1)
    return sym


def run_addr2line(pc: str, mod: str, include_context: bool) -> Optional[str]:
    if not pc or not mod:
        return None
    try:
        # 调用 addr2line 获取函数与位置链（函数名与位置成对出现）
        proc = subprocess.run(
            ["addr2line", "-a", pc, "-e", mod, "-i", "-f", "-s", "-C"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        out = proc.stdout.strip().splitlines()
        if not out:
            return None
        # 输出首行为地址，去掉该行保留后续函数/位置内容
        if out:
            out = out[1:]
        # 将函数与位置配对，并按“调用链自底向上”的顺序插入，便于与栈序对应
        frames: List[str] = []
        it = iter(out)
        for func in it:
            loc = next(it, "?")
            if include_context:
                frames.insert(0, f"{func}:{loc}")
            else:
                frames.insert(0, func)
        return ";".join(frames)
    except Exception:
        return None


def build_frame_name(
    symbol: str,
    dso: str,
    annotate_kernel: bool,
    annotate_jit: bool,
    include_addrs: bool,
) -> str:
    name = symbol
    if not include_addrs:
        name = strip_addr_offset(name)
    # 为内核模块追加标注
    if annotate_kernel and is_kernel_dso_perl_like(dso):
        if not name.endswith("_[k]"):
            name = f"{name}_[k]"
    # 为 JIT 模块追加标注
    if annotate_jit and is_jit_dso_perl_like(dso):
        if not name.endswith("_[j]"):
            name = f"{name}_[j]"
    return name


def read_lines(path: str):
    if path == "-":
        for line in sys.stdin:
            yield line.rstrip("\n")
    else:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                yield line.rstrip("\n")


def collapse(args: argparse.Namespace) -> Dict[str, int]:
    annotate_kernel = args.kernel or args.annotate_all
    annotate_jit = args.jit or args.annotate_all

    collapsed: Dict[str, int] = defaultdict(int)

    current_comm: Optional[str] = None
    current_pid: Optional[str] = None
    current_tid: Optional[str] = None
    current_event: Optional[str] = None
    current_period: Optional[int] = None
    event_filter = args.event_filter.strip()
    first_event: Optional[str] = None

    frames: List[Tuple[str, str, Optional[str], Optional[str]]] = []
    # 帧数据列表： (ip, symbol, dso, srcline)

    def flush_record():
        nonlocal frames, current_comm, current_pid, current_tid, current_event, current_period
        # 结束当前样本：若只有进程名也输出一条记录，便于统计空栈样本
        if not frames and not current_comm:
            return
        current_comm_local = current_comm or "unknown"

        # 事件过滤：若未显式提供过滤名，则以首次出现的事件名作为默认过滤值
        nonlocal first_event
        if not event_filter:
            if first_event is None and current_event:
                first_event = current_event
            ef = first_event
        else:
            ef = event_filter
        if ef and current_event and current_event != ef:
            frames = []
            return

        # 进程显示名，按选项追加 PID 或 PID/TID
        annotate_proc = current_comm_local
        if args.include_tid and current_pid and current_tid:
            annotate_proc = f"{annotate_proc} {current_pid}/{current_tid}"
        elif args.include_pid and current_pid:
            annotate_proc = f"{annotate_proc} {current_pid}"

        # 构建折叠栈：左侧靠近入口，右侧为叶子；首段为进程名
        stack_parts: List[str] = [annotate_proc]
        # 使输出为“入口在左，叶子在右”，因此按帧列表做逆序遍历
        for ip, sym, dso, srcline in frames[::-1]:
            # 若启用内联展开且有模块信息，尝试将同一地址的内联链展开为多段帧
            inlined = None
            if (
                args.do_inline
                and ip
                and dso
                and dso not in ("[unknown]", "[unknown] (deleted)")
            ):
                inlined = run_addr2line(ip, dso, args.context)
            if inlined:
                for part in inlined.split(";"):
                    stack_parts.append(
                        build_frame_name(
                            part, dso, annotate_kernel, annotate_jit, args.addrs
                        )
                    )
                continue

            # 若启用 srcline，则将源位置信息并入符号显示
            if args.srcline and srcline:
                sym_disp = f"{sym}:{srcline}"
            else:
                sym_disp = sym

            # 规范化：将分号替换为冒号，避免与折叠分隔符冲突
            sym_disp = sym_disp.replace(";", ":")

            # 处理内联链：以 '->' 拆分同一栈帧内的内联函数序列
            parts = [p for p in sym_disp.split("->") if p]

            # 规范化未知符号：若符号为 [unknown] 且模块已知，则用模块基名表示；可选包含地址
            normalized_parts: List[str] = []
            for p in parts:
                func = p
                if func.strip() == "[unknown]":
                    if dso and dso.strip() != "[unknown]":
                        base = os.path.basename(dso)
                        inner = base
                    else:
                        inner = "unknown"
                    if args.addrs and ip:
                        func = f"[{inner} <{ip}>]"
                    else:
                        func = f"[{inner}]"
                # 进一步清理：去除引号；去除括号中的内容（匿名命名空间除外）
                func = func.replace('"', "").replace("'", "")
                if not re.search(r"\.\(.*\)\.", func):
                    func = re.sub(r"\((?!anonymous namespace\)).*", "", func)
                normalized_parts.append(func)

            # 追加当前帧的内联链；为保持“入口在左”，内联链也按逆序追加
            if normalized_parts:
                for func in normalized_parts[::-1]:
                    frame_name = build_frame_name(
                        func, dso or "", annotate_kernel, annotate_jit, args.addrs
                    )
                    stack_parts.append(frame_name)
                continue

            frame_name = build_frame_name(
                sym_disp, dso or "", annotate_kernel, annotate_jit, args.addrs
            )
            stack_parts.append(frame_name)

        key = ";".join(stack_parts)
        # 样本权重：若 header 中提供了周期(period)则用之，否则默认 1
        period = current_period if current_period is not None else 1
        collapsed[key] += int(period)
        frames = []

    # 读取并解析每行文本
    for raw in read_lines(args.infile):
        line = raw.rstrip()
        if not line:
            # 空行表示样本结束，触发输出并清理状态
            flush_record()
            current_comm = current_pid = current_tid = current_event = None
            current_period = None
            continue

        m = HEADER_PERL_HEAD_RE.match(line)
        if m:
            # 新样本开始；如果之前有未输出的样本，先输出
            flush_record()
            current_comm = m.group(1)
            current_pid = m.group(2)
            current_tid = m.group(3) or current_pid
            # 解析尾部的周期与事件名
            pe = HEADER_PERL_TAIL_RE.search(line)
            if pe:
                current_period = int(pe.group(1)) if pe.group(1) else 1
                current_event = pe.group(2)
            else:
                # 行以冒号结尾则视为无显式周期/事件
                if HEADER_ONLY_COLON_LINE_RE.match(line):
                    current_period = 1
                    current_event = None
                else:
                    current_period = 1
                    current_event = None
            # 规范化进程名：空格替换为下划线，避免与折叠分隔符冲突
            if current_comm:
                current_comm = current_comm.replace(" ", "_")
            frames = []
            continue

        # 解析栈帧行
        fm = FRAME_RE.match(line) or FRAME_NOIP_RE.match(line)
        if fm:
            if fm.re is FRAME_RE:
                ip = fm.group(1)
                rawfunc = fm.group(2)
                dso = fm.group(3)
            else:
                ip = ""
                rawfunc = fm.group(1)
                dso = fm.group(2)
            # 去除符号中的地址偏移（+0x...）
            sym = re.sub(r"\+0x[0-9A-Fa-f]+$", "", rawfunc)
            srcline = None
            # 若符号未知或缺失，用地址或占位符替代（取决于 --addrs）
            if sym.strip() == "[unknown]" or sym.strip() == "[unknown] ":
                pass
            elif not sym or sym.strip() == "?":
                sym = ip if args.addrs and ip else "[unknown]"
            frames.append((ip, sym, dso, srcline))
            continue

        # 其他行可能为额外元信息，这里忽略

    # 文件结束：输出剩余样本
    flush_record()
    return collapsed


def main() -> int:
    args = parse_args()
    try:
        collapsed = collapse(args)
    except KeyboardInterrupt:
        return 130
    except BrokenPipeError:
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # 输出折叠栈；按字典序排序，便于后续处理与比对
    out = sys.stdout
    try:
        for stack in sorted(collapsed.keys()):
            print(f"{stack} {collapsed[stack]}", file=out)
    except BrokenPipeError:
        return 0
    try:
        out.flush()
    except BrokenPipeError:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
