import logging
from pathlib import Path
import subprocess
import time
from typing import List, Optional
from src.collector import start_perf_stat, start_sar, stop_perf_stat, stop_sar
from src.config_loader import load_workload_config
from src.executor import ExecutionError, run_command, run_in_background
from src.static_collector import collect_all_static_info
import yaml
import tempfile
import shutil

log = logging.getLogger(__name__)


def run_sampling(
    config_path: Optional[Path],
    output_path: Path,
    workload_name: Optional[str] = None,
    intensities: Optional[List[int]] = None,
    attach_pids: Optional[str] = None,
    duration_override: Optional[int] = None,
    no_static_info: bool = False,
):
    """
    Core logic for the sampling workflow. Supports calibrated, direct, and attach modes.
    采样工作流的核心逻辑。支持校准模式、直接模式和依附模式。

    :param config_path: Path to calibrated YAML config (calibrated mode).
    :param output_path: Path to save the final .pipa archive.
    :param workload_name: Name of the workload (for direct/attach mode).
    :param intensities: List of intensities to sample (for direct mode).
    :param attach_pids: Process ID(s) to attach to (for attach mode).
    :param duration_override: Override sampling duration in seconds.
    :param no_static_info: Skip collection of static system information.
    """
    log.info("🚀 Starting sampling process...")
    log.info(f"  -> Output will be saved to: {output_path.name}")

    # --- 1. 收集静态信息 (可选) ---
    if not no_static_info:
        log.info("Collecting static system information...")
        try:
            static_info = collect_all_static_info()
        except Exception as e:
            log.error(f"Failed to collect static info: {e}", exc_info=True)
            raise
        log.debug(f"Collected static info: {static_info}")
    else:
        log.info("Skipping static system information collection as requested.")
        static_info = None

    # --- 2. 创建临时工作目录 ---
    work_dir = Path(tempfile.mkdtemp(prefix="pipa_sample_"))
    log.info(f"Created temporary working directory: {work_dir}")

    try:
        # 将静态信息写入文件 (可选)
        if static_info:
            static_info_path = work_dir / "static_info.yaml"
            with open(static_info_path, "w") as f:
                yaml.dump(static_info, f, default_flow_style=False)
            log.info(f"Saved static info to {static_info_path}")

        # --- 核心逻辑分支 ---
        config = {}
        load_levels_map = {}

        if config_path:
            # --- 校准模式 ---
            log.info(f"Running in CALIBRATED mode using {config_path.name}")
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)

            load_levels_map = {
                level: conf.get("intensity")
                for level, conf in config.get("calibrated_parameters", {}).items()
            }
            if not load_levels_map:
                raise ValueError("Config is missing 'calibrated_parameters'.")

        elif workload_name and intensities:
            # --- 直接模式 ---
            log.info(
                f"Running in DIRECT mode for workload '{workload_name}' "
                f"with intensities: {intensities}"
            )
            config = load_workload_config(workload_name)

            # 构造一个与校准模式兼容的 map
            load_levels_map = {f"intensity_{i}": i for i in intensities}

        elif attach_pids:
            # --- 依附模式 (attach 模式是主要判断条件) ---
            log.info(f"Running in ATTACH mode, attaching to PID(s): {attach_pids}")

            if workload_name:
                # 如果提供了 workload，就加载它来获取 collectors
                log.info(f"Using workload configuration: {workload_name}")
                config = load_workload_config(workload_name)
            else:
                # 如果没提供，使用默认配置
                log.info(
                    "No workload specified, using default collector configuration."
                )
                config = {
                    "workload_name": "default",
                    "collectors": {
                        "macro": [
                            {
                                "name": "perf_stat",
                                "enabled": True,
                                "mode": "pid",
                                "event_groups": [
                                    ["cycles", "instructions"],
                                    ["cache-references", "cache-misses"],
                                ],
                            }
                        ]
                    },
                }

            # 在依附模式下，我们只有一个"level"，即"attach"
            # intensity 在这里没有意义，但我们为了复用循环，可以设为 0
            load_levels_map = {"attach": 0}

        else:
            raise ValueError("Invalid arguments: Inconsistent sampling mode.")

        # --- 统一的采集循环 ---
        current_workload_name = config.get("workload_name", "Unknown")
        log.info(f"  -> Workload identified: {current_workload_name}")
        log.info(f"  -> Load levels to sample: {list(load_levels_map.keys())}")

        for level, intensity in load_levels_map.items():
            log.info(f"--- Starting collection for level: '{level}' ---")

            # 为当前等级创建一个子目录
            level_dir = work_dir / level
            level_dir.mkdir()
            log.info(f"Created subdirectory for '{level}': {level_dir}")

            target_pid = None
            benchmark_proc = None

            if attach_pids:
                # --- 依附模式的特殊逻辑 ---
                target_pid = attach_pids
                log.info(f"Using provided PID(s): {target_pid}")
            else:
                # --- 主动模式的逻辑 (启动压测 & 获取 PID) ---
                driver = config.get("benchmark_driver", {})
                command_template = driver.get("command_template")
                if not command_template:
                    raise ValueError(
                        "Missing 'command_template' in benchmark_driver config."
                    )

                # 启动压测
                benchmark_cmd = command_template.format(intensity=intensity)
                log.info(f"Starting benchmark for '{level}': {benchmark_cmd}")
                benchmark_proc = run_in_background(benchmark_cmd)

                # 等待压测进程稳定并获取 PID
                time.sleep(5)
                pid_command = driver.get("target_pid_command")
                if pid_command:
                    try:
                        pid_output = run_command(pid_command).strip()
                        target_pid = pid_output
                        log.info(f"Target PID(s) for '{level}' are: {target_pid}")
                    except (ExecutionError, ValueError, IndexError) as e:
                        log.warning(
                            f"Could not determine target PID: {e}."
                            " Some collectors may fail."
                        )

            # 启动压测
            log.info(f"Starting Phase 1: Macro-Metrics Collection for '{level}'...")

            macro_collectors_config = config.get("collectors", {}).get("macro", [])
            running_macro_collectors = {}
            macro_duration = 0

            for collector_conf in macro_collectors_config:
                if not collector_conf.get("enabled", False):
                    continue

                proc = None
                collector_name = collector_conf.get("name")
                output_file = None

                if collector_name == "perf_stat":
                    output_file = level_dir / "perf_stat.txt"
                    perf_args = {
                        "output_file": str(output_file),
                        "mode": collector_conf.get("mode", "system"),
                        "event_groups": collector_conf.get("event_groups", []),
                        "all_threads": collector_conf.get("all_threads", False),
                        "interval": collector_conf.get("interval"),
                    }
                    if perf_args["mode"] == "pid":
                        if not target_pid:
                            log.warning(
                                "Skipping perf_stat in pid mode: target_pid not found."
                            )
                            continue
                        perf_args["target_pid"] = target_pid
                    proc = start_perf_stat(**perf_args)

                elif collector_name == "sar_cpu":
                    output_file = level_dir / "sar_cpu.txt"
                    duration = collector_conf.get("duration", 60)
                    interval = collector_conf.get("interval", 1)
                    proc = start_sar(
                        duration=duration,
                        interval=interval,
                        output_file=str(output_file),
                    )

                if proc:
                    running_macro_collectors[proc.pid] = {
                        "proc": proc,
                        "name": collector_name,
                        "output_file": output_file,
                        "duration": collector_conf.get("duration", 60),
                    }
                    macro_duration = max(
                        macro_duration, collector_conf.get("duration", 60)
                    )

            # 如果提供了 duration_override，则覆盖计算出的 macro_duration
            if duration_override is not None:
                macro_duration = duration_override
                log.info(
                    f"Duration overridden to {duration_override} seconds "
                    f"via --duration option."
                )

            if running_macro_collectors:
                log.info(
                    f"Macro-metrics collection running for {macro_duration} seconds..."
                )
                time.sleep(macro_duration)

                # --- 关键！在依附模式下，我们不停止任何压测进程 ---
                if not attach_pids and benchmark_proc is not None:
                    # --- 主动模式的清理逻辑 ---
                    if benchmark_proc.poll() is None:
                        log.info(
                            f"Stopping benchmark process "
                            f"(PID: {benchmark_proc.pid})..."
                        )
                        benchmark_proc.terminate()
                        try:
                            benchmark_proc.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            log.warning(
                                "Benchmark process did not terminate gracefully."
                                " Killing it..."
                            )
                            benchmark_proc.kill()
                            benchmark_proc.wait()

                log.info("Stopping macro-metrics collectors...")
                for pid, collector_context in running_macro_collectors.items():
                    proc = collector_context["proc"]
                    name = collector_context["name"]
                    output_file = collector_context["output_file"]
                    duration = collector_context["duration"]

                    if output_file is None:
                        log.warning(
                            f"Collector '{name}' (PID: {pid}) has no output file,"
                            " skipping stop logic."
                        )
                        continue

                    wait_timeout = duration + 15
                    if name == "perf_stat":
                        content = stop_perf_stat(
                            proc, str(output_file), timeout=wait_timeout
                        )
                        if content:
                            log.debug(
                                f"--- perf_stat.txt content for '{level}' ---\n"
                                f"{content}\n--------------------"
                            )
                    elif name == "sar_cpu":
                        stop_sar(proc, str(output_file), duration=duration)
                    proc = collector_context["proc"]
                    name = collector_context["name"]
                    output_file = collector_context["output_file"]
                    duration = collector_context["duration"]

            log.info(f"--- Collection for level '{level}' finished. ---")

        # --- 4. 打包归档 ---
        log.info(f"Archiving results from {work_dir} to {output_path}...")
        archive_base_name = str(output_path.with_suffix(""))
        archive_path_with_ext = shutil.make_archive(
            base_name=archive_base_name, format="gztar", root_dir=work_dir
        )

        final_archive_path = Path(archive_path_with_ext)
        final_archive_path.rename(output_path)
        log.info(f"✅ Successfully created archive: {output_path}")

    finally:
        # --- 5. 清理 ---
        log.info(f"Cleaning up temporary directory: {work_dir}")
        shutil.rmtree(work_dir)
