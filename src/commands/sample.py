from pathlib import Path
from typing import Optional

import click

from src.engine.sample import run_sampling


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
    required=True,
    help="Attach to an existing process ID (or comma-separated list).",
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
def sample(
    output_path_str: str,
    attach_pid_str: str,
    duration_stat: int,
    duration_record: int,
    no_stat: bool,
    no_record: bool,
    perf_stat_interval: Optional[int],
    sar_interval: Optional[int],
    perf_record_freq: Optional[int],
    perf_events: Optional[str],
    no_static_info: bool,
):
    """
    Captures a standardized, two-phase performance snapshot.
    Phase 1: Macro-scan (perf stat + sar).
    Phase 2: Micro-profiling (perf record for flamegraphs).
    """
    if no_stat and no_record:
        raise click.UsageError("Cannot specify both --no-stat and --no-record. At least one phase must run.")

    output_path = Path(output_path_str)

    try:
        run_sampling(
            output_path=output_path,
            attach_pids=attach_pid_str,
            duration_stat=duration_stat,
            duration_record=duration_record,
            run_stat_phase=not no_stat,
            run_record_phase=not no_record,
            perf_stat_interval=perf_stat_interval,
            sar_interval=sar_interval,
            perf_record_freq=perf_record_freq,
            perf_events_override=perf_events,
            no_static_info=no_static_info,
        )
        total_duration = (duration_stat if not no_stat else 0) + (duration_record if not no_record else 0)
        click.secho(f"✅ Sampling complete ({total_duration}s). Snapshot saved to: {output_path}", fg="green")
    except Exception as e:
        click.secho(f"❌ An error occurred during the sampling process: {e}", fg="red")
        raise click.Abort()
