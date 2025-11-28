# src/pipa/report/hotspots.py
import logging
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


def extract_hotspots(
    perf_data_path: Path, symfs_dir: Optional[str] = None, kallsyms_path: Optional[str] = None, max_rows: int = 100
) -> List[Dict[str, Any]]:
    """
    运行 perf report 解析热点函数。
    支持指定 symfs (用户态符号) 和 kallsyms (内核符号)。
    """
    if not perf_data_path.exists():
        return []

    # 构造基础命令
    # --stdio: 文本输出
    # --no-children: 不累计子调用
    # --call-graph none: 强制关闭调用栈打印 (关键！防止正则匹配到堆栈行)
    # -n: 显示样本数
    cmd = [
        "perf",
        "report",
        "-i",
        str(perf_data_path),
        "--stdio",
        "--no-children",
        "--call-graph",
        "none",
        "-n",
        "--sort",
        "comm,dso,symbol",
    ]

    # [Feature] 支持离线/异地符号解析
    if symfs_dir:
        # --symfs 指定带有 debuginfo 的根目录结构
        cmd.extend(["--symfs", symfs_dir])

    if kallsyms_path:
        # --kallsyms 指定内核符号表
        cmd.extend(["--kallsyms", kallsyms_path])

    hotspots = []
    try:
        log.info(f"Running perf extraction: {' '.join(cmd)}")
        # 显式设置 LC_ALL=C 避免中文环境导致的乱码或格式变异

        # === DEBUG 核心：把 perf report 的原始输出打印出来 ===
        result = subprocess.run(cmd, capture_output=True, text=True, check=False, env={"LC_ALL": "C"})
        if log.isEnabledFor(logging.DEBUG):
            log.debug("--- [DEBUG] Raw Perf Report Output (Stdout) ---")
            log.debug(result.stdout[:2000] + "..." if len(result.stdout) > 2000 else result.stdout)
            if result.stderr:
                log.debug("--- [DEBUG] Raw Perf Report Error (Stderr) ---")
                log.debug(result.stderr)
        # ========================================================

        if result.returncode != 0:
            log.warning(f"perf report failed (rc={result.returncode}): {result.stderr.strip()}")
            return []

        # 解析逻辑
        # 典型行: 44.01%  15505  gzip  gzip  [.] deflate
        # 正则: Overhead(浮点), Samples(整), Comm(非空), DSO(非空), Symbol(剩余所有)
        pattern = re.compile(r"^\s*([0-9\.]+)%\s+(\d+)\s+(\S+)\s+(\S+)\s+(.+)$")

        for line in result.stdout.splitlines():
            line = line.strip()
            # 跳过注释行和空行
            if not line or line.startswith("#"):
                continue

            match = pattern.match(line)
            if match:
                overhead, samples, comm, dso, symbol = match.groups()

                # === 清洗尾部的 IPC/Coverage 数据 ===
                # perf report 的 symbol 列可能包含 " -      -" 这样的尾巴
                symbol = re.sub(r"\s+-\s+-\s*$", "", symbol).strip()
                # ==========================================

                # 符号清洗与分类
                scope = "Unknown"
                clean_symbol = symbol

                if "[.]" in symbol:
                    scope = "User"
                    clean_symbol = symbol.replace("[.]", "").strip()
                elif "[k]" in symbol:
                    scope = "Kernel"
                    clean_symbol = symbol.replace("[k]", "").strip()
                elif "[g]" in symbol:
                    scope = "Guest"
                    clean_symbol = symbol.replace("[g]", "").strip()

                hotspots.append(
                    {
                        "Overhead": float(overhead),  # 转为数字方便前端排序
                        "Samples": int(samples),
                        "Process": comm,
                        "Library": dso,
                        "Symbol": clean_symbol,
                        "Scope": scope,
                    }
                )

                if len(hotspots) >= max_rows:
                    break

    except FileNotFoundError:
        log.warning("Command 'perf' not found. Cannot extract hotspots.")
    except Exception as e:
        log.warning(f"Exception during hotspot extraction: {e}")

    return hotspots
