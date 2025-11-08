from pathlib import Path


def get_project_root() -> Path:
    """
    查找并返回项目根目录。

    此实现依赖于一个约定：此文件位于：
    `{project_root}/src/utils.py`。它对直接源代码执行和可编辑安装都有效。
    """
    return Path(__file__).resolve().parent.parent
