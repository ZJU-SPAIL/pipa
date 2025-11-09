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
    "--duration",
    type=int,
    required=True,
    help="The sampling duration in seconds for all collectors.",
)
@click.option(
    "--collectors-config",
    "collectors_config_path",
    default=None,
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Optional path to a YAML file defining custom collectors.",
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
    duration: int,
    collectors_config_path: Optional[str],
    no_static_info: bool,
):
    """
    Attaches to running processes and captures a performance snapshot.
    This is the core data collection command of pipa.
    """
    output_path = Path(output_path_str)

    try:
        run_sampling(
            output_path=output_path,
            attach_pids=attach_pid_str,
            duration=duration,
            collectors_config_path=collectors_config_path,
            no_static_info=no_static_info,
        )
        click.secho(f"✅ Sampling complete. Snapshot saved to: {output_path}", fg="green")
    except Exception as e:
        click.secho(f"❌ An error occurred during the sampling process: {e}", fg="red")
        raise click.Abort()
