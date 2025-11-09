from pathlib import Path
from typing import Optional

import click


@click.command()
@click.option(
    "--input-a",
    "input_a_path_str",
    required=True,
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to the first .pipa archive (baseline).",
)
@click.option(
    "--input-b",
    "input_b_path_str",
    required=True,
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to the second .pipa archive (comparison target).",
)
@click.option(
    "--output",
    "output_path_str",
    required=False,
    type=click.Path(writable=True, dir_okay=False, resolve_path=True),
    default=None,
    help="Path to save the generated HTML comparison report.",
)
def compare(input_a_path_str: str, input_b_path_str: str, output_path_str: Optional[str]):
    """
    Compares two pipa snapshots and generates a comparison report.
    """
    from src.engine.compare import run_comparison

    input_a_path = Path(input_a_path_str)
    input_b_path = Path(input_b_path_str)
    output_path = Path(output_path_str) if output_path_str else None

    try:
        terminal_report = run_comparison(input_a_path, input_b_path, output_path)

        click.secho("\n--- PIPA Performance Comparison (Terminal Summary) ---", fg="cyan", bold=True)
        click.echo(terminal_report)

        if output_path:
            click.secho(f"\n✅ Full comparison report saved to: {output_path}", fg="green")

    except Exception as e:
        click.secho(f"❌ An error occurred during the comparison: {e}", fg="red")
        raise click.Abort()
