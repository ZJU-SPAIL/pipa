"""
基础sar解析器模块

此模块提供通用的sar生成的CSV文件解析功能。
处理sar输出的特殊格式，包括注释头和分号分隔符。
"""

from io import StringIO
from pathlib import Path

import pandas as pd


def generic_sar_parse(file_path: Path) -> pd.DataFrame:
    """
    健壮的通用解析器，用于所有sar生成的CSV文件。

    此函数封装了处理注释头和分号分隔符的共享逻辑。
    自动检测并处理sar输出的格式特点。

    参数:
        file_path: 要解析的CSV文件路径。

    返回:
        解析后的pandas DataFrame。
    """
    if not file_path.exists() or file_path.stat().st_size == 0:
        return pd.DataFrame()

    with open(file_path, "r", errors="ignore") as f:
        lines = f.readlines()

    header_line_content = None
    data_start_index = 0

    for i, line in enumerate(lines):
        if line.strip().startswith("#"):
            header_line_content = line.strip()[1:].strip()
            data_start_index = i + 1
            break

    if not header_line_content:
        return pd.read_csv(file_path, sep=";")

    csv_content = header_line_content + "\n" + "".join(lines[data_start_index:])
    return pd.read_csv(StringIO(csv_content), sep=";")
