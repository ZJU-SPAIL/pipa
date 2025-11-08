import logging

import click

from src.engine.calibrate import run_calibration

log = logging.getLogger(__name__)


@click.command()
@click.option(
    "--workload",
    required=True,
    help="The name of the workload to calibrate (e.g., mysql).",
)
@click.option(
    "--output-config",
    "output_config_path",
    required=True,
    help="Path to save the calibrated YAML configuration.",
)
def calibrate(workload, output_config_path):
    """
    Calibrates the environment for a specific workload to find optimal load parameters.
    """
    try:
        run_calibration(workload, output_config_path)
        click.secho(f"✅ Calibration for '{workload}' completed successfully.", fg="green")
    except Exception as e:
        click.secho(f"❌ Calibration for '{workload}' failed. See logs for details.", fg="red")
        log.debug(f"CLI caught exception: {e}", exc_info=True)
        raise click.Abort()
