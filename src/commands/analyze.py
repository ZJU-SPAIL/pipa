import shutil
import tempfile
from pathlib import Path
from typing import Optional

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
@click.option(
    "--html-report",
    "html_report_path_str",
    default=None,
    type=click.Path(writable=True, dir_okay=False, resolve_path=True),
    help="Path to save the generated HTML report.",
)
def analyze(input_path_str: str, html_report_path_str: Optional[str]):
    """Analyzes results and runs the data alignment PoC."""
    input_path = Path(input_path_str)
    html_report_path = Path(html_report_path_str) if html_report_path_str else None

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
            result_df = run_analysis_poc(level_dir, html_report_path)
            if result_df is not None and not result_df.empty:
                click.echo("--- Merged DataFrame Head (Console Output): ---")
                click.echo(result_df.head().to_markdown(index=False))

            if html_report_path:
                click.secho(f"\n✅ HTML report saved to: {html_report_path}", fg="green")
            else:
                click.secho("\n✅ PoC executed successfully.", fg="green")
        except Exception as e:
            click.secho(f"❌ An error occurred during analysis PoC: {e}", fg="red")
            raise click.Abort()
