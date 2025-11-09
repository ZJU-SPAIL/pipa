from pathlib import Path

import click

from src.engine.flamegraph import generate_flamegraph_from_snapshot


@click.command()
@click.option(
    "--input",
    "input_path_str",
    required=True,
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to the .pipa archive containing perf.data.",
)
@click.option(
    "--output",
    "output_path_str",
    required=True,
    type=click.Path(writable=True, dir_okay=False, resolve_path=True),
    help="Path to save the generated Flame Graph SVG file.",
)
def flamegraph(input_path_str: str, output_path_str: str):
    """
    Generates an interactive Flame Graph from a .pipa snapshot.
    """
    input_path = Path(input_path_str)
    output_path = Path(output_path_str)

    try:
        click.echo(f"🔥 Generating Flame Graph from '{input_path.name}'...")
        generate_flamegraph_from_snapshot(input_path, output_path)
        click.secho(f"✅ Flame Graph successfully saved to: {output_path}", fg="green")
    except Exception as e:
        click.secho(f"❌ An error occurred during Flame Graph generation: {e}", fg="red")
        raise click.Abort()
