import shutil
import tempfile
from pathlib import Path

import click

from src.engine.analyze import run_analysis_poc


@click.command()
@click.option(
    "--input",
    "input_path_str",
    required=True,
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to the .pipa archive to analyze.",
)
def analyze(input_path_str: str):
    """Analyzes results from a .pipa archive and runs the data alignment PoC."""
    input_path = Path(input_path_str)

    with tempfile.TemporaryDirectory(prefix="pipa_analyze_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        click.echo(f"Unpacking archive {input_path.name} to {temp_dir}...")
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
            result_df = run_analysis_poc(level_dir)
            if result_df is not None and not result_df.empty:
                click.echo("--- Merged DataFrame Head: ---")
                click.echo(result_df.head().to_markdown(index=False))
            click.secho("\n✅ PoC executed successfully.", fg="green")
        except Exception as e:
            click.secho(f"❌ An error occurred during analysis PoC: {e}", fg="red")
            raise click.Abort()
