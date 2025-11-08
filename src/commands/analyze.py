import shutil
import tempfile
from pathlib import Path

import click

from src.engine.analyze import generate_report


@click.command()
@click.option(
    "--input",
    "input_path_str",
    required=True,
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to the .pipa archive to analyze.",
)
@click.option(
    "--output",
    "output_path_str",
    required=True,
    type=click.Path(writable=True, dir_okay=False, resolve_path=True),
    help="Path to save the generated HTML report.",
)
def analyze(input_path_str: str, output_path_str: str):
    """Analyzes sampling results and generates a comprehensive HTML report."""
    input_path = Path(input_path_str)
    output_path = Path(output_path_str)

    with tempfile.TemporaryDirectory(prefix="pipa_analyze_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        click.echo(f"Unpacking archive '{input_path.name}' for analysis...")
        shutil.unpack_archive(input_path, temp_dir, format="gztar", filter="data")

        level_dir = None
        for item in temp_dir.iterdir():
            if item.is_dir():
                level_dir = item
                break

        if not level_dir:
            click.secho("Error: No data directories found in the archive.", fg="red")
            raise click.Abort()

        try:
            generate_report(level_dir, output_path)
            click.secho(f"\n✅ Analysis complete. Report saved to: {output_path}", fg="green")
        except Exception as e:
            click.secho(f"❌ An error occurred during report generation: {e}", fg="red")
            raise click.Abort()
