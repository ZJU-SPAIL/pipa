from pathlib import Path

import click
import yaml

from src.static_collector import collect_all_static_info


@click.command()
@click.option(
    "--output",
    "output_path_str",
    required=False,
    type=click.Path(writable=True, dir_okay=False, resolve_path=True),
    default="pipa_static_info.yaml",
    help="Path to save the static system information YAML file.",
)
def healthcheck(output_path_str: str):
    """
    Collects static system information and saves it to a file.
    This allows for faster, more precise sampling with the `sample` command.
    """
    output_path = Path(output_path_str)
    try:
        click.echo("🚀 Collecting static system information...")
        static_info = collect_all_static_info()

        with open(output_path, "w") as f:
            yaml.dump(static_info, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        click.secho(f"✅ Static information successfully saved to: {output_path}", fg="green")

    except Exception as e:
        click.secho(f"❌ An error occurred during health check: {e}", fg="red")
        raise click.Abort()
