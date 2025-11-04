import click
from src.commands.calibrate import calibrate
from src.logger_setup import setup_logging


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


# Placeholders for future commands
# 为未来命令保留的占位符
@cli.command()
def sample():
    """(Placeholder) Runs the automated sampling process."""
    click.echo("This is the 'sample' command. Not yet implemented.")


@cli.command()
def analyze():
    """(Placeholder) Analyzes results and generates a report."""
    click.echo("This is the 'analyze' command. Not yet implemented.")


if __name__ == "__main__":
    cli()
