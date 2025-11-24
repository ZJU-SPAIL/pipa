"""
命令行接口模块

此模块定义了PIPA工具的命令行接口，使用click框架。
提供主要的CLI入口点和子命令注册。
"""

from importlib.metadata import PackageNotFoundError, version

import click

from src.logger_setup import setup_logging
from src.pipa.commands.analyze import analyze
from src.pipa.commands.compare import compare
from src.pipa.commands.flamegraph import flamegraph
from src.pipa.commands.healthcheck import healthcheck
from src.pipa.commands.sample import sample

try:
    __version__ = version("pipa")
except PackageNotFoundError:
    __version__ = "unknown"


@click.group()
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase verbosity. -v for INFO, -vv for DEBUG.",
)
@click.version_option(version=__version__)
def cli(verbose: int):
    """
    PIPA (Performance Insight & Profiling Agent)

    一款纯粹的、非侵入式性能快照与诊断工具。
    """
    setup_logging(verbose)


cli.add_command(sample)
cli.add_command(analyze)
cli.add_command(compare)
cli.add_command(healthcheck)
cli.add_command(flamegraph)


if __name__ == "__main__":
    cli()
