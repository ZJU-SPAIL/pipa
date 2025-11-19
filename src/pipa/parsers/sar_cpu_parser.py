"""
sar CPU解析器模块

此模块解析sar_cpu.csv文件并应用CPU特定的转换。
基于通用sar解析器，添加CPU列的特殊处理。
"""

from pathlib import Path

import pandas as pd

from ._base_sar_parser import generic_sar_parse


def parse(file_path: Path) -> pd.DataFrame:
    """
    解析sar_cpu.csv并应用CPU特定的转换。

    使用通用sar解析器解析文件，然后对CPU列进行特殊处理，
    将-1转换为'all'表示所有CPU的聚合数据。

    参数:
        file_path: sar_cpu.csv文件的路径。

    返回:
        解析并转换后的DataFrame。
    """
    df = generic_sar_parse(file_path)
    if not df.empty and "CPU" in df.columns:
        df["CPU"] = df["CPU"].astype(str)
        df.loc[df["CPU"] == "-1", "CPU"] = "all"
    return df
