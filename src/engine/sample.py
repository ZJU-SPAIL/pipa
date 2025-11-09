import logging
import platform
import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional

import yaml

from src.collector import start_perf_stat, start_sar, stop_perf_stat, stop_sar
from src.config_loader import load_events_config, load_yaml_config
from src.static_collector import collect_all_static_info

log = logging.getLogger(__name__)

# --- Pipa 的新灵魂：内置的默认采集器 ---
# 当用户不提供自定义配置时，我们将使用这套标准的、通用的配置。
DEFAULT_COLLECTORS_CONFIG = {
    "collectors": {
        "macro": [
            {
                "name": "perf_stat",
                "enabled": True,
                "mode": "pid",
                "all_threads": True,
                "interval": 1000,
                "events_profile": "cpu_basic",
            },
            {"name": "sar_cpu", "enabled": True, "interval": 1},
        ]
    }
}


def run_sampling(
    output_path: Path,
    attach_pids: str,
    duration: int,
    collectors_config_path: Optional[str] = None,
    no_static_info: bool = False,
):
    """
    Core logic for the attach-only sampling workflow.
    """
    log.info("🚀 Starting sampling process (Attach Mode)...")
    log.info(f"  -> Attaching to PID(s): {attach_pids}")
    log.info(f"  -> Duration: {duration} seconds")
    log.info(f"  -> Output will be saved to: {output_path.name}")

    if not no_static_info:
        log.info("Collecting static system information...")
        static_info = collect_all_static_info()
    else:
        log.info("Skipping static system information collection.")
        static_info = None

    host_arch = platform.machine()
    cpu_model_name = static_info.get("cpu_info", {}).get("Model_Name", "") if static_info else ""
    events_config = load_events_config(host_arch, cpu_model_name)

    work_dir = Path(tempfile.mkdtemp(prefix="pipa_sample_"))
    log.info(f"Created temporary working directory: {work_dir}")

    try:
        if static_info:
            static_info_path = work_dir / "static_info.yaml"
            with open(static_info_path, "w") as f:
                yaml.dump(static_info, f, default_flow_style=False)

        if collectors_config_path:
            log.info(f"Using custom collectors from: {collectors_config_path}")
            config = load_yaml_config(collectors_config_path)
        else:
            log.info("Using default built-in collector configuration.")
            config = DEFAULT_COLLECTORS_CONFIG

        level_dir = work_dir / "attach_session"
        level_dir.mkdir()

        log.info("--- Starting Macro-Metrics Collection ---")

        macro_collectors_config = config.get("collectors", {}).get("macro", [])
        running_macro_collectors = {}

        for collector_conf in macro_collectors_config:
            if not collector_conf.get("enabled", False):
                continue
            proc = None
            output_file = None
            output_bin_file = None
            collector_name = collector_conf.get("name")

            if collector_name == "perf_stat":
                output_file = level_dir / "perf_stat.txt"
                profile_name = collector_conf.get("events_profile")
                event_groups = events_config.get(profile_name, [])
                proc = start_perf_stat(
                    output_file=str(output_file),
                    mode="pid",
                    target_pid=attach_pids,
                    event_groups=event_groups,
                    interval=collector_conf.get("interval"),
                )
            elif collector_name == "sar_cpu":
                output_bin_file = level_dir / "sar_cpu.bin"
                interval = collector_conf.get("interval", 1)
                proc = start_sar(
                    duration=duration,
                    interval=interval,
                    output_bin_file=str(output_bin_file),
                )

            if proc:
                context = {"proc": proc, "name": collector_name}
                if collector_name == "sar_cpu":
                    context["output_bin_file"] = output_bin_file
                    context["output_csv_file"] = level_dir / "sar_cpu.csv"
                else:
                    context["output_file"] = output_file
                running_macro_collectors[proc.pid] = context

        if running_macro_collectors:
            log.info(f"Collection running for {duration} seconds...")
            time.sleep(duration)
            log.info("Stopping macro-metrics collectors...")

            for pid, collector_context in running_macro_collectors.items():
                proc = collector_context["proc"]
                name = collector_context["name"]
                wait_timeout = duration + 15

                if name == "perf_stat":
                    stop_perf_stat(proc, str(collector_context["output_file"]), timeout=wait_timeout)
                elif name == "sar_cpu":
                    stop_sar(
                        proc,
                        output_bin_file=str(collector_context["output_bin_file"]),
                        output_csv_file=str(collector_context["output_csv_file"]),
                        timeout=wait_timeout,
                    )
        log.info("--- Collection finished. ---")

        log.info(f"Archiving results from {work_dir} to {output_path}...")
        archive_base_name = str(output_path.with_suffix(""))
        archive_path_with_ext = shutil.make_archive(base_name=archive_base_name, format="gztar", root_dir=work_dir)
        Path(archive_path_with_ext).rename(output_path)
        log.info(f"✅ Successfully created archive: {output_path}")

    finally:
        log.info(f"Cleaning up temporary directory: {work_dir}")
        shutil.rmtree(work_dir)
