"""
命令行接口模块

此模块定义了PIPA工具的命令行接口，使用click框架。
提供主要的CLI入口点和子命令注册。
"""

import click

from src.logger_setup import setup_logging
from src.pipa.commands.analyze import analyze
from src.pipa.commands.compare import compare
from src.pipa.commands.flamegraph import flamegraph
from src.pipa.commands.healthcheck import healthcheck
from src.pipa.commands.sample import sample


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
    一个纯净的命令行性能快照工具。

    根据详细程度参数配置日志记录。
    """
    setup_logging(verbose)
    setup_logging(verbose)


cli.add_command(sample)
cli.add_command(analyze)
cli.add_command(compare)
cli.add_command(healthcheck)
cli.add_command(flamegraph)


if __name__ == "__main__":
    cli()
