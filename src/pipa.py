import click

from .commands.analyze import analyze
from .commands.sample import sample
from .logger_setup import setup_logging


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


cli.add_command(sample)
cli.add_command(analyze)


if __name__ == "__main__":
    cli()
