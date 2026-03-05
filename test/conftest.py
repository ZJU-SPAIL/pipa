"""Test configuration utilities."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if SRC_PATH.is_dir():
    sys.path.insert(0, str(SRC_PATH))
