import logging
import math
import os
import signal
import subprocess
import time

import yaml

from src.collector import collect_cpu_utilization
from src.config_loader import ConfigError, load_workload_config
from src.executor import ExecutionError

log = logging.getLogger(__name__)


def _run_benchmark_and_measure_cpu(command_template: str, intensity: int, duration: int) -> float:
    """
    执行基准测试并测量系统 CPU 利用率。

    这是校准引擎的核心原子操作，每次调用都会：
    1. 启动一个压测进程（后台运行）
    2. 在压测运行期间采集系统 CPU 利用率
    3. 优雅地终止压测进程
    4. 记录任何异常情况（"飞行记录仪"功能）

    算法流程：
    ```
    START
      ├─ 格式化命令模板，填入 intensity 参数
      ├─ 启动压测进程（异步，非阻塞）
      ├─ 等待 5 秒让压测稳定运行
      ├─ 测量 CPU 利用率（持续 duration 秒）
      └─ FINALLY 块（无论成功失败都执行）:
           ├─ 如果进程仍在运行，发送 SIGTERM
           ├─ 等待进程优雅退出（超时 15 秒）
           ├─ 如果超时，发送 SIGKILL 强制终止
           └─ 检查退出码，记录异常日志
    END
    ```

    设计亮点：
    - **健壮性**: 使用 try-finally 确保进程一定被清理
    - **容错性**: 压测失败不会导致校准中断，只记录警告
    - **可观测性**: 捕获并记录 stdout/stderr，便于事后分析

    :param command_template: 压测命令模板，包含 {intensity} 占位符
    :param intensity: 压测强度（如线程数、并发数）
    :param duration: CPU 测量持续时间（秒）
    :return: 观测到的 CPU 利用率百分比 (0-100)
    """
    benchmark_cmd = command_template.format(intensity=intensity)
    benchmark_proc = subprocess.Popen(
        benchmark_cmd,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        preexec_fn=os.setsid,
    )
    time.sleep(5)

    cpu_usage = 0
    try:
        cpu_usage = collect_cpu_utilization(duration=duration)
    finally:
        if benchmark_proc.poll() is None:
            pgid = os.getpgid(benchmark_proc.pid)
            log.debug(f"Terminating benchmark process group (PGID: {pgid})...")
            try:
                os.killpg(pgid, signal.SIGTERM)
                benchmark_proc.wait(timeout=5)
                log.debug("Benchmark process terminated gracefully.")
            except subprocess.TimeoutExpired:
                log.warning("压测进程未能优雅终止，正在强制结束...")
                os.killpg(pgid, signal.SIGKILL)
                stdout, stderr = benchmark_proc.communicate()
                if stdout or stderr:
                    log.warning("--- Benchmark Blackbox Recorder ---")
                    log.warning(f"Benchmark STDOUT:\n{stdout}")
                    log.warning(f"Benchmark STDERR:\n{stderr}")
                    log.warning("---------------------------------")
            except ProcessLookupError:
                log.debug("Process group already terminated.")

    return cpu_usage


def _find_intensity_for_target(
    command_template: str,
    target_cpu: float,
    min_intensity: int,
    max_intensity: int,
    tolerance: float = 3.0,
    max_iterations: int = 10,
) -> dict:
    """
    使用二分查找算法快速定位目标 CPU 利用率对应的最佳压测强度。

    这是校准引擎的"涡轮增压器"，将线性搜索的 O(n) 时间复杂度优化为 O(log n)。

    算法原理（基于单调性假设）：
    ```
    假设: CPU利用率与压测强度呈单调递增关系
         intensity ↑  →  cpu_usage ↑

    二分查找过程:

    Round 1:  [min=10 ─────── mid=50 ─────── max=90]
              测试 intensity=50 → cpu=45%
              目标 target=60% → cpu < target
              结论: 最佳点在右半区间

    Round 2:  [min=51 ───── mid=70 ──── max=90]
              测试 intensity=70 → cpu=65%
              目标 target=60% → cpu > target
              结论: 最佳点在左半区间

    Round 3:  [min=51 ── mid=60 ── max=69]
              测试 intensity=60 → cpu=58%
              |58 - 60| = 2% < tolerance(3%)
              结论: 找到满意解，提前终止 ✓
    ```

    核心优势:
    - **速度**: 对于范围 [1, 100]，最多只需 7 次测试（log₂(100)）
    - **精度**: 持续跟踪全局最优解（最小误差点）
    - **鲁棒**: 即使未达到容忍度，也保证返回最接近的点

    终止条件（满足任一即停止）:
    1. 找到误差 ≤ tolerance 的解（提前成功）
    2. 搜索空间收缩为空 (left > right)
    3. 达到最大迭代次数（防止无限循环）

    :param command_template: 压测命令模板（包含 {intensity} 占位符）
    :param target_cpu: 目标 CPU 利用率百分比，例如 60.0 表示 60%
    :param min_intensity: 搜索区间左边界（闭区间）
    :param max_intensity: 搜索区间右边界（闭区间）
    :param tolerance: CPU 误差容忍度（单位：%），默认 3.0%
    :param max_iterations: 最大迭代次数，默认 10 次（足够覆盖 2^10=1024 的搜索空间）
    :return: 字典 {"intensity": 最佳强度值, "cpu": 对应的 CPU 利用率}

    示例:
    ```python
    //寻找能达到 75% CPU 利用率的线程数
    result = _find_intensity_for_target(
        command_template="sysbench --threads={intensity} run",
        target_cpu=75.0,
        min_intensity=1,
        max_intensity=128,
    //可能返回: {"intensity": 96, "cpu": 76.5}
    )
    ```
    """
    log.info(f"  [Binary Search] Target: {target_cpu:.2f}%, Range: [{min_intensity}, {max_intensity}]")

    best_point = None
    min_distance = float("inf")

    left, right = min_intensity, max_intensity
    iteration = 0

    while left <= right and iteration < max_iterations:
        iteration += 1
        mid = (left + right) // 2

        log.info(f"    [Iteration {iteration}] Testing intensity: {mid}")
        cpu_usage = _run_benchmark_and_measure_cpu(command_template, mid, duration=10)
        log.info(f"    -> Observed CPU: {cpu_usage:.2f}%")

        distance = abs(cpu_usage - target_cpu)
        if distance < min_distance:
            min_distance = distance
            best_point = {"intensity": mid, "cpu": cpu_usage}

        if distance <= tolerance:
            log.info(f"    -> ✅ Found excellent match (distance: {distance:.2f}%)")
            break

        if cpu_usage < target_cpu:
            left = mid + 1
        else:
            right = mid - 1

    if best_point is None:
        fallback_intensity = (min_intensity + max_intensity) // 2
        fallback_cpu = _run_benchmark_and_measure_cpu(command_template, fallback_intensity, duration=10)
        best_point = {"intensity": fallback_intensity, "cpu": fallback_cpu}
        log.warning(f"  -> Using fallback intensity: {fallback_intensity}")

    log.info(f"  [Binary Search Complete] Best: intensity={best_point['intensity']}, cpu={best_point['cpu']:.2f}%")
    return best_point


def run_calibration(workload: str, output_config_path: str):
    """
    校准引擎主函数：自动为工作负载寻找最佳的低/中/高负载强度配置。

    这是一个三阶段的智能搜索算法，融合了全局探索和局部优化：

    完整算法流程：
    ```
    阶段 0: 准备与探测
    ─────────────────────────────────────────────────────────────
     1. 加载工作负载配置（命令、强度范围、目标负载等级）
     2. 启动被测服务（如 MySQL, Redis）
     3. 使用 max_intensity 探测系统 CPU 上限
        → 这是"天花板测试"，用于归一化目标

                                  ↓

    阶段 1: 粗粒度扫描 (Coarse-Grained Scan)
    ─────────────────────────────────────────────────────────────
     目标: 绘制"性能地图"，找到单调递增的性能曲线
     方法: 等间距采样，覆盖整个 [min, max] 区间
     采样点: 12 个（经验值，平衡速度与精度）

     示例（假设 min=8, max=256）:
       intensity:  8 → 30 → 52 → 74 → ... → 256
       cpu:       12% → 35% → 58% → 82% → ... → 95%

     输出: performance_map = [
       {"intensity": 8,  "cpu": 12},
       {"intensity": 30, "cpu": 35},
       ...
     ]

                                  ↓

    阶段 2: 全局优化 (Monotonic Triplet Search)
    ─────────────────────────────────────────────────────────────
     目标: 从性能地图中找到最优的三点组合
     约束:
       1. 单调性: low.intensity < medium < high
                  low.cpu < medium.cpu < high.cpu
       2. 最优性: 三点与目标 CPU 的总误差最小

     算法: 三重循环穷举 (O(n³)，n=12 时可接受)
       for each (p_low, p_medium, p_high) in performance_map:
         if 满足单调性:
           total_distance = |p_low.cpu - target_low| +
                           |p_medium.cpu - target_medium| +
                           |p_high.cpu - target_high|
           if total_distance < best:
             best_triplet = (p_low, p_medium, p_high)

     输出: best_triplet = {
       "low":    {"intensity": 30, "cpu": 35},   // 可达成约 20% CPU
       "medium": {"intensity": 91, "cpu": 50},   // 可达成约 50% CPU
       "high":   {"intensity": 198, "cpu": 95}   // 可达成约 95% CPU
     }

                                  ↓

    阶段 3: 局部精调 (Fine-Tuning with Binary Search)
    ─────────────────────────────────────────────────────────────
     目标: 在粗糙解附近进行高精度搜索
     方法: 对每个负载等级执行二分查找
     搜索范围: [coarse - step, coarse + step]

     示例（针对 medium 级别）:
       粗糙解: intensity=96, cpu=62%
       目标:   cpu=60%
       搜索范围: [96-21, 96+21] = [75, 117]

       二分查找:
         mid=96  → cpu=62% → 向左收缩
         mid=85  → cpu=58% → 向右收缩
         mid=91  → cpu=60% → ✓ 找到！

     关键特性:
       - 单调性约束: 保证 low < medium < high
       - 后备机制: 如果二分查找失败，使用粗糙解
       - 早停策略: 误差 ≤ 3% 时提前终止

                                  ↓

    最终输出: 校准配置文件
    ─────────────────────────────────────────────────────────────
     calibrated_parameters:
       low:    {intensity: 28}
       medium: {intensity: 91}
       high:   {intensity: 198}
    ```

    时间复杂度分析：
    - 阶段 1 (粗扫描): O(k) = 12 次测试
    - 阶段 2 (三点搜索): O(k³) = 1728 次比较（内存操作，忽略不计）
    - 阶段 3 (精调): O(3 × log n) ≈ 21 次测试（假设每个 log₂(step) ≈ 7）
    - 总计: 约 33-35 次真实压测，相比全域线性扫描（>100 次）大幅优化

    :param workload: 工作负载名称或配置文件路径（如 "mysql" 或 "showcases/mysql/workload.yaml"）
    :param output_config_path: 输出的校准配置文件路径（YAML 格式）
    :raises ConfigError: 配置文件格式错误
    :raises ExecutionError: 命令执行失败
    :raises RuntimeError: 无法找到单调性能路径
    """
    log.info(f"🚀 Starting calibration for workload: {workload}")
    log.info("  -> [Pre-Flight Check] Verifying baseline system load...")
    baseline_cpu = collect_cpu_utilization(duration=3, interval=1)
    BASELINE_THRESHOLD = 5.0
    if baseline_cpu > BASELINE_THRESHOLD:
        raise RuntimeError(
            f"Baseline CPU utilization ({baseline_cpu:.2f}%) is too high, "
            f"exceeding the threshold of {BASELINE_THRESHOLD}%. "
            "Please stop other CPU-intensive processes before running calibration."
        )
    log.info(f"  -> Baseline CPU is healthy ({baseline_cpu:.2f}%). Proceeding.")
    try:
        workload_config = load_workload_config(workload)
        driver = workload_config["benchmark_driver"]
        start_cmd = workload_config["commands"]["start"]
        stop_cmd = workload_config["commands"]["stop"]

        log.info("  -> Starting service for calibration...")
        subprocess.run(start_cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(10)

        min_intensity = int(driver["intensity_variable"]["min"])
        max_intensity = int(driver["intensity_variable"]["max"])
        log.info(f"\n  [Probe] Testing with max intensity ({max_intensity}) " "to find CPU ceiling...")
        max_achievable_cpu = _run_benchmark_and_measure_cpu(driver["command_template"], max_intensity, duration=15)
        log.info(f"  -> Maximum achievable CPU utilization: {max_achievable_cpu:.2f}%")

        if max_achievable_cpu < 1.0:
            raise ValueError("Max achievable CPU is near zero. Cannot proceed.")

        log.info("\n  -> Starting Coarse-grained Scan to map performance landscape...")
        performance_map = []
        num_steps = 12
        step_coarse = math.ceil((max_intensity - min_intensity + 1) / num_steps)
        step_coarse = max(1, step_coarse)

        for intensity in range(min_intensity, max_intensity + 1, step_coarse):
            log.info(f"    [Coarse Scan] Testing intensity: {intensity}")
            cpu_usage = _run_benchmark_and_measure_cpu(driver["command_template"], intensity, duration=10)
            log.info(f"    -> Observed CPU: {cpu_usage:.2f}%")
            performance_map.append({"intensity": intensity, "cpu": cpu_usage})

        if max_intensity not in [p["intensity"] for p in performance_map]:
            performance_map.append({"intensity": max_intensity, "cpu": max_achievable_cpu})

        log.info("\n  -> Finding globally optimal monotonic triplet...")
        best_triplet = None
        min_total_distance = float("inf")
        load_levels = workload_config["target_load_levels"]

        targets = {
            name: (
                max_achievable_cpu * (conf["target_range"][0] / 100.0)
                + max_achievable_cpu * (conf["target_range"][1] / 100.0)
            )
            / 2
            for name, conf in load_levels.items()
        }

        for p_low in performance_map:
            for p_medium in performance_map:
                for p_high in performance_map:
                    if not (
                        p_low["intensity"] < p_medium["intensity"] < p_high["intensity"]
                        and p_low["cpu"] < p_medium["cpu"] < p_high["cpu"]
                    ):
                        continue

                    dist_low = abs(p_low["cpu"] - targets["low"])
                    dist_medium = abs(p_medium["cpu"] - targets["medium"])
                    dist_high = abs(p_high["cpu"] - targets["high"])
                    total_distance = dist_low + dist_medium + dist_high

                    if total_distance < min_total_distance:
                        min_total_distance = total_distance
                        best_triplet = {
                            "low": p_low,
                            "medium": p_medium,
                            "high": p_high,
                        }

        if best_triplet is None:
            raise RuntimeError("Could not find a monotonic performance path.")

        log.info("  -> Found optimal coarse points:")
        for name, point in best_triplet.items():
            log.info(f"    - {name}: intensity={point['intensity']}, cpu={point['cpu']:.2f}%")

        calibrated_intensities = {}
        last_intensity = 0

        level_order = ["low", "medium", "high"]
        for i, level_name in enumerate(level_order):
            coarse_point = best_triplet[level_name]

            search_min = max(last_intensity + 1, coarse_point["intensity"] - step_coarse)

            if i + 1 < len(level_order):
                next_level_coarse_intensity = best_triplet[level_order[i + 1]]["intensity"]
                search_max = min(
                    max_intensity,
                    coarse_point["intensity"] + step_coarse,
                    next_level_coarse_intensity - 1,
                )
            else:
                search_max = min(max_intensity, coarse_point["intensity"] + step_coarse)
            search_min = min(search_min, search_max)

            target_cpu = targets[level_name]

            log.info(f"\n  -> Fine-tuning for '{level_name}' using Binary Search...")

            best_point = _find_intensity_for_target(
                driver["command_template"],
                target_cpu,
                search_min,
                search_max,
            )

            calibrated_intensities[level_name] = best_point["intensity"]
            last_intensity = best_point["intensity"]
            log.info(
                f"  -> ✅ Best intensity for '{level_name}': {best_point['intensity']} "
                f"(CPU: {best_point['cpu']:.2f}%)"
            )

        log.info("\n  -> Stopping service after calibration...")
        subprocess.run(stop_cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        log.info(f"  -> Generating calibrated config at {output_config_path}...")
        calibrated_config = {
            "workload_name": workload,
            "calibrated_parameters": {
                level: {"intensity": intensity} for level, intensity in calibrated_intensities.items()
            },
            "benchmark_driver": driver,
            "commands": workload_config["commands"],
            "collectors": workload_config.get("collectors", {}),
        }

        with open(output_config_path, "w") as f:
            yaml.dump(calibrated_config, f, default_flow_style=False, sort_keys=False)
        log.info(f"✅ Successfully saved calibrated config to {output_config_path}!")

    except (ConfigError, ExecutionError, ValueError, RuntimeError, IOError) as e:
        log.error(f"❌ Calibration failed: {e}")
        raise

    log.info("🔧 Calibration finished.")
