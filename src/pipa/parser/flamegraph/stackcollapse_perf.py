# -*- coding: utf-8 -*-
"""
重构版 stackcollapse_perf 模块（函数接口版）
- 解析 `perf script` 文本并生成折叠栈（folded stacks）
- 提供纯 Python 函数接口，便于在上层服务/分析流程中直接调用

设计要点：
- 单一职责函数：解析头/帧、构建输出、I/O 分离
- 关键数据结构封装：SampleRecord、Frame、CollapseOptions
- 扩展点：BottleneckAnalyzerHook（后续可插入策略用于自动瓶颈分析）

核心接口：
- collapse(lines, options, hooks=None) -> Dict[str,int]
- collapse_file(path, options, hooks=None) -> Dict[str,int]
- format_collapsed(collapsed) -> List[str]  # 生成按字典序排序的输出行
- save_collapsed(collapsed, output_path) -> None
"""
from __future__ import annotations
import os
import re
import sys
import subprocess
from dataclasses import dataclass, field
from typing import Dict, Iterable, Iterator, List, Optional, Tuple, Protocol
from collections import defaultdict

# -----------------------------
# 正则与常量（解析相关）
# -----------------------------
HEADER_PERL_HEAD_RE = re.compile(r"^\s*(\S.+?)\s+(\d+)(?:/(\d+))?\s+", re.ASCII)
HEADER_PERL_TAIL_RE = re.compile(r":\s*(\d+)?\s+(\S+):\s*$")
HEADER_ONLY_COLON_LINE_RE = re.compile(r"^\s*(.+?):\s*$")
FRAME_RE = re.compile(r"^\s*([0-9A-Fa-fx]+)\s*(.+) \((.*)\)\s*$")
FRAME_NOIP_RE = re.compile(r"^\s*(.+) \((.*)\)\s*$")
ADDR_OFFSET_RE = re.compile(r"^(.+)\+0x([0-9a-fA-F]+)$")


# -----------------------------
# 数据结构（封装与接口）
# -----------------------------
@dataclass
class Frame:
    ip: str
    symbol: str
    dso: str
    srcline: Optional[str] = None


@dataclass
class SampleRecord:
    comm: Optional[str] = None
    pid: Optional[str] = None
    tid: Optional[str] = None
    event: Optional[str] = None
    period: Optional[int] = None
    frames: List[Frame] = field(default_factory=list)


@dataclass
class CollapseOptions:
    include_pid: bool = False
    include_tid: bool = False
    kernel: bool = False
    jit: bool = False
    annotate_all: bool = False
    addrs: bool = False
    event_filter: str = ""
    do_inline: bool = False
    context: bool = False
    srcline: bool = False


class BottleneckAnalyzerHook(Protocol):
    """扩展点：在折叠生成前后进行分析或变换。"""

    def before_flush(self, record: SampleRecord) -> None: ...

    def after_flush(self, folded_key: str, weight: int) -> None: ...


# -----------------------------
# I/O 与便捷接口
# -----------------------------


def read_lines(path: str) -> Iterator[str]:
    if path == "-":
        for line in sys.stdin:
            yield line.rstrip("\n")
    else:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                yield line.rstrip("\n")


def collapse_file(
    path: str,
    options: CollapseOptions,
    hooks: Optional[List[BottleneckAnalyzerHook]] = None,
) -> Dict[str, int]:
    return collapse(read_lines(path), options, hooks)


def format_collapsed(collapsed: Dict[str, int]) -> List[str]:
    return [f"{stack} {collapsed[stack]}" for stack in sorted(collapsed.keys())]


def save_collapsed(collapsed: Dict[str, int], output_path: str) -> None:
    lines = format_collapsed(collapsed)
    with open(output_path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")


# -----------------------------
# 解析器：头/帧解析与记录构建（纯逻辑）
# -----------------------------


def is_kernel_dso(dso: str) -> bool:
    if not dso:
        return False
    if "unknown" in dso:
        return False
    return dso.startswith("[") or dso.endswith("vmlinux")


def is_jit_dso(dso: str) -> bool:
    if not dso:
        return False
    return re.search(r"/tmp/perf-\d+\.map", dso) is not None


def strip_addr_offset(sym: str) -> str:
    m = ADDR_OFFSET_RE.match(sym)
    return m.group(1) if m else sym


def run_addr2line(pc: str, mod: str, include_context: bool) -> Optional[str]:
    if not pc or not mod:
        return None
    try:
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
        out = out[1:] if out else out
        frames: List[str] = []
        it = iter(out)
        for func in it:
            loc = next(it, "?")
            frames.insert(0, f"{func}:{loc}" if include_context else func)
        return ";".join(frames)
    except Exception:
        return None


def parse_header(
    line: str,
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[int], Optional[str]]:
    m = HEADER_PERL_HEAD_RE.match(line)
    if not m:
        return None, None, None, None, None
    comm = m.group(1)
    pid = m.group(2)
    tid = m.group(3) or pid
    pe = HEADER_PERL_TAIL_RE.search(line)
    if pe:
        period = int(pe.group(1)) if pe.group(1) else 1
        event = pe.group(2)
    else:
        if HEADER_ONLY_COLON_LINE_RE.match(line):
            period = 1
            event = None
        else:
            period = 1
            event = None
    if comm:
        comm = comm.replace(" ", "_")
    return comm, pid, tid, period, event


def parse_frame(line: str) -> Optional[Frame]:
    fm = FRAME_RE.match(line) or FRAME_NOIP_RE.match(line)
    if not fm:
        return None
    if fm.re is FRAME_RE:
        ip = fm.group(1)
        rawfunc = fm.group(2)
        dso = fm.group(3)
    else:
        ip = ""
        rawfunc = fm.group(1)
        dso = fm.group(2)
    sym = re.sub(r"\+0x[0-9A-Fa-f]+$", "", rawfunc)
    # 保持原脚本行为：若为 "[unknown]" 或 "[unknown] " 则保留原符号（包含空格）
    if sym.strip() == "[unknown]" or sym.strip() == "[unknown] ":
        pass
    elif not sym or sym.strip() == "?":
        # 用占位符；地址是否附加由构建阶段依据 --addrs 决定
        sym = "[unknown]"
    return Frame(ip=ip, symbol=sym, dso=dso, srcline=None)


# -----------------------------
# 构建器：折叠键生成（纯逻辑）
# -----------------------------


def build_frame_name(
    symbol: str,
    dso: str,
    annotate_kernel: bool,
    annotate_jit: bool,
    include_addrs: bool,
) -> str:
    name = symbol if include_addrs else strip_addr_offset(symbol)
    if annotate_kernel and is_kernel_dso(dso):
        if not name.endswith("_[k]"):
            name = f"{name}_[k]"
    if annotate_jit and is_jit_dso(dso):
        if not name.endswith("_[j]"):
            name = f"{name}_[j]"
    return name


def normalize_symbol(sym: str) -> str:
    sym = sym.replace(";", ":").replace('"', "").replace("'", "")
    if not re.search(r"\.\(.*\)\.", sym):
        sym = re.sub(r"\((?!anonymous namespace\)).*", "", sym)
    return sym


def expand_inline(
    ip: str, dso: str, do_inline: bool, include_context: bool
) -> Optional[List[str]]:
    if not (
        do_inline and ip and dso and dso not in ("[unknown]", "[unknown] (deleted)")
    ):
        return None
    inlined = run_addr2line(ip, dso, include_context)
    return inlined.split(";") if inlined else None


def build_folded_key(record: SampleRecord, options: CollapseOptions) -> Tuple[str, int]:
    annotate_kernel = options.kernel or options.annotate_all
    annotate_jit = options.jit or options.annotate_all

    annotate_proc = record.comm or "unknown"
    if options.include_tid and record.pid and record.tid:
        annotate_proc = f"{annotate_proc} {record.pid}/{record.tid}"
    elif options.include_pid and record.pid:
        annotate_proc = f"{annotate_proc} {record.pid}"

    parts: List[str] = [annotate_proc]
    for frame in record.frames[::-1]:
        inline_parts = expand_inline(
            frame.ip, frame.dso, options.do_inline, options.context
        )
        if inline_parts:
            for part in inline_parts:
                parts.append(
                    build_frame_name(
                        part, frame.dso, annotate_kernel, annotate_jit, options.addrs
                    )
                )
            continue
        sym_disp = (
            f"{frame.symbol}:{frame.srcline}"
            if options.srcline and frame.srcline
            else frame.symbol
        )
        # 与历史脚本一致：先替换分号，再按 '->' 拆分；未知符号替换发生在去引号与去括号之前
        sym_disp = sym_disp.replace(";", ":")
        seq = [p for p in sym_disp.split("->") if p]
        normalized_seq: List[str] = []
        for p in seq:
            func = p
            if func.strip() == "[unknown]":
                if frame.dso and frame.dso.strip() != "[unknown]":
                    base = os.path.basename(frame.dso)
                    inner = base
                else:
                    inner = "unknown"
                if options.addrs and frame.ip:
                    func = f"[{inner} <{frame.ip}>]"
                else:
                    func = f"[{inner}]"
            func = func.replace('"', "").replace("'", "")
            if not re.search(r"\.\(.*\)\.", func):
                func = re.sub(r"\((?!anonymous namespace\)).*", "", func)
            normalized_seq.append(func)
        if normalized_seq:
            for func in normalized_seq[::-1]:
                parts.append(
                    build_frame_name(
                        func,
                        frame.dso or "",
                        annotate_kernel,
                        annotate_jit,
                        options.addrs,
                    )
                )
            continue
        parts.append(
            build_frame_name(
                sym_disp, frame.dso or "", annotate_kernel, annotate_jit, options.addrs
            )
        )

    key = ";".join(parts)
    period = record.period if record.period is not None else 1
    return key, int(period)


# -----------------------------
# 主流程：读取 -> 解析 -> 构建 -> 输出（可插入 Hook）
# -----------------------------


def collapse(
    lines: Iterable[str],
    options: CollapseOptions,
    hooks: Optional[List[BottleneckAnalyzerHook]] = None,
) -> Dict[str, int]:
    hooks = hooks or []
    collapsed: Dict[str, int] = defaultdict(int)
    first_event: Optional[str] = None

    current = SampleRecord()

    def should_pass_event_filter(event: Optional[str]) -> bool:
        nonlocal first_event
        ef = options.event_filter or first_event
        # 设置默认过滤事件为首次出现的事件
        if not options.event_filter and first_event is None and event:
            first_event = event
            ef = first_event
        if ef and event and event != ef:
            return False
        return True

    def flush_record() -> None:
        nonlocal current
        if not current.frames and not current.comm:
            current = SampleRecord()
            return
        if not should_pass_event_filter(current.event):
            current = SampleRecord()
            return
        for h in hooks:
            h.before_flush(current)
        key, weight = build_folded_key(current, options)
        collapsed[key] += weight
        for h in hooks:
            h.after_flush(key, weight)
        current = SampleRecord()

    for raw in lines:
        line = raw.rstrip()
        if not line:
            flush_record()
            current = SampleRecord()
            continue
        comm, pid, tid, period, event = parse_header(line)
        if comm is not None:
            flush_record()
            current = SampleRecord(
                comm=comm, pid=pid, tid=tid, period=period, event=event
            )
            continue
        frame = parse_frame(line)
        if frame:
            current.frames.append(frame)
            continue
        # 其他行忽略

    flush_record()
    return collapsed
