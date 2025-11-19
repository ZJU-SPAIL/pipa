import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional

import click

from src.collector import start_perf_record, start_perf_stat, start_sar, stop_perf_record, stop_perf_stat, stop_sar

log = logging.getLogger(__name__)


def _run_sampling(
    output_path: Path,
    attach_pids: str,
    system_wide: bool,
    duration_stat: int,
    duration_record: int,
    run_stat_phase: bool,
    run_record_phase: bool,
    perf_stat_interval: Optional[int],
    sar_interval: Optional[int],
    perf_record_freq: Optional[int],
    perf_events_override: Optional[str],
    no_static_info: bool,
    static_info_path: Optional[Path] = None,
):
    """
    Executes the new two-phase sampling workflow.
    """
    total_duration = (duration_stat if run_stat_phase else 0) + (duration_record if run_record_phase else 0)
    log.info("🚀 Starting standardized two-phase sampling process...")
    if system_wide:
        log.info("  -> Mode: System-Wide (all CPUs, all processes)")
    else:
        log.info(f"  -> Mode: Process-Specific, Attaching to PID(s): {attach_pids}")
    log.info(f"  -> Total Duration: {total_duration} seconds")
    log.info(f"  -> Output will be saved to: {output_path.name}")

    if not system_wide:
        pids_to_check = attach_pids.split(",")
        for pid_str in pids_to_check:
            try:
                pid = int(pid_str)
                if pid <= 0:
                    raise ValueError
                os.kill(pid, 0)
            except (ValueError, ProcessLookupError):
                raise click.UsageError(f"Process with PID '{pid_str}' does not exist.")
            except PermissionError:
                raise click.UsageError(
                    f"No permission to attach to process with PID '{pid_str}'. " "Try running pipa with sudo."
                )

    work_dir = Path(tempfile.mkdtemp(prefix="pipa_sample_"))
    log.info(f"Created temporary working directory: {work_dir}")

    try:
        static_info_found_and_handled = False

        if static_info_path:
            log.info(f"Using explicitly provided static info from: {static_info_path}")
            shutil.copy(static_info_path, work_dir / "static_info.yaml")
            static_info_found_and_handled = True

        if not static_info_found_and_handled:
            default_static_info_path = Path.cwd() / "pipa_static_info.yaml"
            if default_static_info_path.exists():
                log.info(f"Found and using default static info file: {default_static_info_path.name}")
                shutil.copy(default_static_info_path, work_dir / "static_info.yaml")
                static_info_found_and_handled = True

        if no_static_info:
            log.info("Skipping static system information collection as requested by --no-static-info flag.")

        elif not static_info_found_and_handled:
            error_msg = (
                "For maximum sampling precision, a pre-collected static information file is required.\n"
                "Please run `pipa healthcheck` in this directory first, or provide a file using "
                "`--static-info-file`."
            )
            raise click.UsageError(error_msg)

        level_dir = work_dir / "attach_session"
        level_dir.mkdir()

        if run_stat_phase:
            log.info(f"--- Starting Phase 1: Macro-Scan for {duration_stat}s ---")
            running_collectors = {}

            # 定义TMA metrics列表 - 使用perf官方的Top-Down Microarchitecture Analysis metrics
            tma_metrics = ["backend_bound", "frontend_bound", "retiring", "bad_speculation"]

            perf_proc = start_perf_stat(
                target_pid=attach_pids,
                system_wide=system_wide,
                interval=perf_stat_interval,
                events_override_str=perf_events_override,
                metrics_list=tma_metrics,
            )
            if perf_proc:
                running_collectors[perf_proc.pid] = {
                    "proc": perf_proc,
                    "name": "perf_stat",
                    "output_file": level_dir / "perf_stat.txt",
                }

            sar_proc = start_sar(
                duration=duration_stat,
                interval=sar_interval or 1,
                output_bin_file=str(level_dir / "sar_all.bin"),
            )
            if sar_proc:
                running_collectors[sar_proc.pid] = {
                    "proc": sar_proc,
                    "name": "sar_cpu",
                    "output_bin_file": level_dir / "sar_all.bin",
                }

            if running_collectors:
                log.info(f"Phase 1 collectors running for {duration_stat} seconds...")
                time.sleep(duration_stat)

                log.info("Stopping Phase 1 collectors...")
                for pid, ctx in running_collectors.items():
                    if ctx["name"] == "perf_stat":
                        stop_perf_stat(ctx["proc"], str(ctx["output_file"]), timeout=duration_stat + 15)
                    elif ctx["name"] == "sar_cpu":
                        stop_sar(
                            ctx["proc"],
                            str(ctx["output_bin_file"]),
                            level_dir,
                            timeout=duration_stat + 15,
                        )

        if run_record_phase:
            log.info(f"--- Starting Phase 2: Micro-Profiling for {duration_record}s ---")
            perf_record_output = level_dir / "perf.data"
            record_proc = start_perf_record(
                target_pid=attach_pids,
                output_file=str(perf_record_output),
                freq=perf_record_freq,
            )
            if record_proc:
                log.info(f"Phase 2 collector (perf record) running for {duration_record} seconds...")
                time.sleep(duration_record)
                log.info("Stopping Phase 2 collector...")
                stop_perf_record(record_proc, timeout=duration_record + 15)

        log.info("--- All collection phases finished. ---")

        log.info(f"Archiving results from {work_dir} to {output_path}...")
        archive_base_name = str(output_path.with_suffix(""))
        archive_path_with_ext = shutil.make_archive(base_name=archive_base_name, format="gztar", root_dir=work_dir)
        Path(archive_path_with_ext).rename(output_path)
        log.info(f"✅ Successfully created archive: {output_path}")

    finally:
        log.info(f"Cleaning up temporary directory: {work_dir}")
        shutil.rmtree(work_dir)


@click.command()
@click.option(
    "--output",
    "output_path_str",
    required=True,
    type=click.Path(writable=True, dir_okay=False, resolve_path=True),
    help="Path to save the final .pipa archive.",
)
@click.option(
    "--attach-to-pid",
    "attach_pid_str",
    required=False,
    default=None,
    help="Attach to an existing process ID (or comma-separated list).",
)
@click.option(
    "--system-wide",
    is_flag=True,
    default=False,
    help="Run collectors in system-wide mode instead of attaching to a PID.",
)
@click.option(
    "--duration-stat",
    type=int,
    default=60,
    show_default=True,
    help="Duration (seconds) for Phase 1 (perf stat + sar).",
)
@click.option(
    "--duration-record",
    type=int,
    default=60,
    show_default=True,
    help="Duration (seconds) for Phase 2 (perf record for flamegraph).",
)
@click.option("--no-stat", is_flag=True, default=False, help="Disable Phase 1 (perf stat + sar).")
@click.option("--no-record", is_flag=True, default=False, help="Disable Phase 2 (perf record).")
@click.option(
    "--perf-stat-interval",
    type=int,
    default=None,
    help="Interval (milliseconds) for perf stat sampling.",
)
@click.option("--sar-interval", type=int, default=None, help="Interval (seconds) for sar sampling.")
@click.option("--perf-record-freq", type=int, default=None, help="Sampling frequency (Hz) for perf record.")
@click.option(
    "--perf-events",
    type=str,
    default=None,
    help="Expert: Comma-separated list to override built-in perf events.",
)
@click.option(
    "--no-static-info",
    is_flag=True,
    default=False,
    help="Skip the collection of static system information.",
)
@click.option(
    "--static-info-file",
    "static_info_path_str",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    default=None,
    help="Path to a pre-collected static info YAML file (from `pipa healthcheck`).",
)
def sample(
    output_path_str: str,
    attach_pid_str: str,
    system_wide: bool,
    duration_stat: int,
    duration_record: int,
    no_stat: bool,
    no_record: bool,
    perf_stat_interval: Optional[int],
    sar_interval: Optional[int],
    perf_record_freq: Optional[int],
    perf_events: Optional[str],
    no_static_info: bool,
    static_info_path_str: Optional[str],
):
    """
    Captures a standardized, two-phase performance snapshot.
    Phase 1: Macro-scan (perf stat + sar).
    Phase 2: Micro-profiling (perf record for flamegraphs).
    """
    if system_wide and attach_pid_str:
        raise click.UsageError("Cannot specify both --attach-to-pid and --system-wide.")
    if not system_wide and not attach_pid_str:
        raise click.UsageError("Must specify either --attach-to-pid or --system-wide.")

    if no_stat and no_record:
        raise click.UsageError("Cannot specify both --no-stat and --no-record. At least one phase must run.")

    output_path = Path(output_path_str)

    try:
        _run_sampling(
            output_path=output_path,
            attach_pids=attach_pid_str,
            system_wide=system_wide,
            duration_stat=duration_stat,
            duration_record=duration_record,
            run_stat_phase=not no_stat,
            run_record_phase=not no_record,
            perf_stat_interval=perf_stat_interval,
            sar_interval=sar_interval,
            perf_record_freq=perf_record_freq,
            perf_events_override=perf_events,
            no_static_info=no_static_info,
            static_info_path=Path(static_info_path_str) if static_info_path_str else None,
        )
        total_duration = (duration_stat if not no_stat else 0) + (duration_record if not no_record else 0)
        click.secho(f"✅ Sampling complete ({total_duration}s). Snapshot saved to: {output_path}", fg="green")
    except Exception as e:
        click.secho(f"❌ An error occurred during the sampling process: {e}", fg="red")
        raise click.Abort()
