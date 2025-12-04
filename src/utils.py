"""
工具函数模块

此模块包含项目通用的工具函数，如获取项目根目录等。
"""

from pathlib import Path
from typing import Union

import pandas as pd


def p95(x: Union[pd.Series, pd.DataFrame]) -> Union[float, pd.Series]:
    """计算 Series 或 DataFrame 的 P95 (第95百分位点)。"""
    return x.quantile(0.95)


def get_project_root() -> Path:
    """
    查找并返回项目根目录。

    此实现依赖于一个约定：此文件位于 `{project_root}/src/utils.py`。
    它对直接源代码执行和可编辑安装都有效。

    返回:
        项目根目录的Path对象。
    """
    return Path(__file__).resolve().parent.parent
