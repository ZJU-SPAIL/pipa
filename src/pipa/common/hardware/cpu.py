from pipa.common.cmd import run_command
from psutil import cpu_count
import os
import platform


def get_cpu_cores():
    """
    返回 CPU 核心编号列表，跨平台兼容。

    优先使用平台专属命令：
    - Linux: `lscpu -p=cpu`（去除注释行）
    - macOS (Darwin): `sysctl -n hw.ncpu` 或 Python `os.cpu_count()` 回退
    - 其他平台：直接使用 Python `os.cpu_count()` 回退

    当命令不可用或执行失败时，优雅降级为 `[0..N-1]`，其中 N 取自 `os.cpu_count()` 或 `psutil.cpu_count()`。
    """
    system = platform.system().lower()
    # Linux 路径：尽可能保留原逻辑
    if system == "linux":
        try:
            cpu_list = [
                l
                for l in run_command("lscpu -p=cpu", log=False).split("\n")
                if l and not l.startswith("#")
            ]
            # 输出为每行一个 core id（字符串），转换为 int 列表
            return [int(x) for x in cpu_list]
        except Exception:
            # 回退到 os/psutil
            pass
    # macOS 路径：使用 sysctl 或 os.cpu_count
    if system == "darwin":
        try:
            out = run_command("sysctl -n hw.ncpu", log=False)
            n = int(out.strip())
            return list(range(n))
        except Exception:
            pass
    # 通用回退：os.cpu_count 或 psutil
    n = os.cpu_count() or cpu_count(logical=True) or 1
    return list(range(int(n)))


NUM_CORES_PHYSICAL = cpu_count(logical=False)  # Number of physical cores
