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
        # 只有在 run_calibration 成功完成（没有抛出任何异常）时，才会执行这里
        click.secho(
            f"✅ Calibration for '{workload}' completed successfully.", fg="green"
        )
    except Exception as e:
        # 只有在 run_calibration 抛出异常时，才会进入这个 except 块
        # 异常已经被 engine 层 log 记录，这里只负责向用户显示最终的失败状态并中断
        click.secho(
            f"❌ Calibration for '{workload}' failed. See logs for details.", fg="red"
        )
        # 可以在这里选择性地打印 e 的信息，帮助快速定位问题
        log.debug(f"CLI caught exception: {e}", exc_info=True)
        raise click.Abort()
