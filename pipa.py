import click
from src.commands.calibrate import calibrate
from src.commands.sample import sample
from src.logger_setup import setup_logging
from src.commands.analyze import analyze


@click.group()
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Increase verbosity. -v for INFO, -vv for DEBUG.",
)
def cli(verbose: int):
    """
    PIPA (An Adaptive Performance Experimentation Platform)
    An adaptive, command-line performance experimentation platform.
    """
    setup_logging(verbose)


# Register commands from submodules
# 从子模块中注册命令
cli.add_command(calibrate)
cli.add_command(sample)
cli.add_command(analyze)


if __name__ == "__main__":
    cli()
