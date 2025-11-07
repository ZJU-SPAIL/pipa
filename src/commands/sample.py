import click
from pathlib import Path
from src.engine.sample import run_sampling
from typing import List, Optional


@click.command()
@click.option(
    "--config",
    "config_path_str",
    default=None,
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to the calibrated YAML configuration file.",
)
@click.option(
    "--output",
    "output_path_str",
    required=True,
    type=click.Path(writable=True, dir_okay=False, resolve_path=True),
    help="Path to save the final .pipa archive.",
)
@click.option(
    "--workload",
    "workload_name",
    default=None,
    help="Workload name for direct sampling (e.g., 'stress_cpu')."
    " Required if --intensity is used.",
)
@click.option(
    "--intensity",
    "intensity_str",
    default=None,
    help="A single intensity or comma-separated list for "
    "direct sampling (e.g., '32' or '8,16,32').",
)
@click.option(
    "--attach-to-pid",
    "attach_pid_str",
    default=None,
    help="Attach to an existing process ID (or comma-separated list). "
    "This is a passive monitoring mode.",
)
@click.option(
    "--duration",
    "duration",
    type=int,
    default=None,
    help="Override the sampling duration in seconds for all collectors.",
)
@click.option(
    "--no-static-info",
    "no_static_info",
    is_flag=True,
    default=False,
    help="Skip the collection of static system information.",
)
def sample(
    config_path_str: Optional[str],
    output_path_str: str,
    workload_name: Optional[str],
    intensity_str: Optional[str],
    attach_pid_str: Optional[str],
    duration: Optional[int],
    no_static_info: bool,
):
    """Runs sampling in calibrated, direct, or passive attach mode."""
    # --- 参数校验 ---
    is_calibrated_mode = bool(config_path_str)
    is_direct_mode = bool(intensity_str)
    is_attach_mode = bool(attach_pid_str)

    # 1. 统计激活了多少种模式
    mode_count = sum([is_calibrated_mode, is_direct_mode, is_attach_mode])

    # 2. 检查模式的互斥性与存在性
    if mode_count > 1:
        raise click.UsageError(
            "Modes are mutually exclusive. Please use only one of: "
            "--config, --intensity, or --attach-to-pid."
        )
    if mode_count == 0:
        raise click.UsageError(
            "You must specify a mode: --config, --intensity, or --attach-to-pid."
        )

    # 3. 检查每种模式的依赖参数是否完备
    if is_direct_mode and not workload_name:
        raise click.UsageError("--workload is required when using --intensity.")

    if is_attach_mode and not duration:
        raise click.UsageError("--duration is required when using --attach-to-pid.")

    # 校验 direct 模式的参数完备性
    if is_direct_mode and not (intensity_str and workload_name):
        raise click.UsageError(
            "--workload and --intensity must be provided together for direct mode."
        )

    config_path = Path(config_path_str) if config_path_str else None
    output_path = Path(output_path_str)

    intensities: List[int] = []
    if intensity_str:
        try:
            intensities = [int(i.strip()) for i in intensity_str.split(",")]
        except ValueError:
            raise click.UsageError(
                "--intensity must be a number or comma-separated numbers."
            )

    # 解析 attach_pid_str
    attach_pids = attach_pid_str if attach_pid_str else None

    try:
        run_sampling(
            config_path,
            output_path,
            workload_name,
            intensities,
            attach_pids,
            duration,
            no_static_info,
        )
        click.secho("✅ Sampling process completed successfully.", fg="green")
    except Exception as e:
        click.secho(f"❌ An error occurred during the sampling process: {e}", fg="red")
        raise click.Abort()
