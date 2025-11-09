import shutil
import tempfile
from pathlib import Path

import click

from src.engine.analyze import generate_report


def get_unique_output_path(base_path: Path) -> Path:
    """
    Generate a unique output file path by appending a number if the file exists.
    E.g., report.html -> report_1.html -> report_2.html, etc.
    """
    if not base_path.exists():
        return base_path

    stem = base_path.stem
    suffix = base_path.suffix
    parent = base_path.parent

    counter = 1
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
        counter += 1


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
    required=False,
    type=click.Path(writable=True, dir_okay=False, resolve_path=True),
    default=None,
    help="Path to save the generated HTML report. If not specified, generates 'report.html' in current directory.",
)
def analyze(input_path_str: str, output_path_str: str):
    """Analyzes sampling results and generates a comprehensive HTML report."""
    input_path = Path(input_path_str)

    if output_path_str is None:
        output_path = get_unique_output_path(Path("report.html").resolve())
    else:
        output_path = Path(output_path_str)
        if output_path.exists():
            output_path = get_unique_output_path(output_path)

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
