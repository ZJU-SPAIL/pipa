import click

from src.logger_setup import setup_logging

# --- 核心修改: 更新所有导入路径 ---
from src.pipa.commands.analyze import analyze
from src.pipa.commands.compare import compare
from src.pipa.commands.flamegraph import flamegraph
from src.pipa.commands.healthcheck import healthcheck
from src.pipa.commands.sample import sample

# --- 修改结束 ---


@click.group()
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase verbosity. -v for INFO, -vv for DEBUG.",
)
def cli(verbose: int):
    """
    PIPA (A Pure Performance Snapshot Tool)
    A pure, command-line performance snapshot tool.
    """
    setup_logging(verbose)


cli.add_command(sample)
cli.add_command(analyze)
cli.add_command(compare)
cli.add_command(healthcheck)
cli.add_command(flamegraph)


if __name__ == "__main__":
    cli()
