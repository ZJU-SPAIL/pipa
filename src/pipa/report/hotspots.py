"""Hotspot extraction helpers built on ``perf report``."""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


def extract_hotspots(
    perf_data_path: Path,
    symfs_dir: Optional[str] = None,
    kallsyms_path: Optional[str] = None,
    max_rows: int = 100,
) -> List[Dict[str, Any]]:
    """Run ``perf report`` and parse the hottest symbols."""

    if not perf_data_path.exists():
        return []

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

    if symfs_dir:
        cmd.extend(["--symfs", symfs_dir])
    if kallsyms_path:
        cmd.extend(["--kallsyms", kallsyms_path])

    hotspots: List[Dict[str, Any]] = []
    try:
        log.info("Running perf extraction: %s", " ".join(cmd))
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False, env={"LC_ALL": "C"}
        )
        if log.isEnabledFor(logging.DEBUG):
            lines = result.stdout.split("\n")[:10]
            useful_lines = [
                line
                for line in lines
                if line.strip()
                and not line.startswith(".")
                and not line.startswith("#")
                and "Overhead" not in line
            ]
            if useful_lines:
                log.debug("--- [DEBUG] Perf Report Summary ---")
                for line in useful_lines[:5]:
                    log.debug("  %s", line.strip())
            if result.stderr:
                log.debug("--- [DEBUG] Perf Report Warnings ---")
                for line in result.stderr.split("\n"):
                    if "Warning" in line or "lost" in line:
                        log.debug("  %s", line.strip())

        if result.returncode != 0:
            log.warning(
                "perf report failed (rc=%s): %s",
                result.returncode,
                result.stderr.strip(),
            )
            return []

        pattern = re.compile(r"^\s*([0-9\.]+)%\s+(\d+)\s+(\S+)\s+(\S+)\s+(.+)$")
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = pattern.match(line)
            if match:
                overhead, samples, comm, dso, symbol = match.groups()
                symbol = re.sub(r"\s+-\s+-\s*$", "", symbol).strip()
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
                        "Overhead": round(float(overhead), 2),
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
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("Exception during hotspot extraction: %s", exc)

    return hotspots
