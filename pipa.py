import logging
import click
import yaml
from src.collector import collect_cpu_utilization
from src.config_loader import load_workload_config, ConfigError
from src.executor import run_command, ExecutionError, run_in_background
import time

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


@click.group()
def cli():
    """
    PIPA (An Adaptive Performance Experimentation Platform)
    An adaptive, command-line performance experimentation platform.
    """
    pass


def _run_benchmark_and_measure_cpu(
    command_template: str, intensity: int, duration: int
) -> float:
    """
    A helper to run benchmark at a given intensity and measure CPU usage.
    一个辅助函数，用于在给定强度下运行基准测试并测量CPU使用率。
    """
    benchmark_cmd = command_template.format(intensity=intensity)
    benchmark_proc = run_in_background(benchmark_cmd)
    # Give benchmark a moment to ramp up
    # 给基准测试一些预热时间
    time.sleep(5)

    cpu_usage = 0
    try:
        cpu_usage = collect_cpu_utilization(duration=duration)
    finally:
        # Always ensure the benchmark process is stopped
        # 总是确保压测进程被停止
        if benchmark_proc.poll() is None:
            benchmark_proc.terminate()
            benchmark_proc.wait(timeout=5)
    return cpu_usage


@cli.command()
@click.option(
    "--workload",
    required=True,
    help="The name of the workload to calibrate (e.g., mysql).",
)
@click.option(
    "--output-config",
    required=True,
    help="Path to save the calibrated YAML configuration.",
)
def calibrate(workload, output_config):
    """
    Calibrates the environment for a specific workload to find optimal load
    parameters.
    """
    click.echo(f"🚀 Starting calibration for workload: {workload}")
    try:
        workload_config = load_workload_config(workload)
        driver = workload_config["benchmark_driver"]
        start_cmd = workload_config["commands"]["start"]
        stop_cmd = workload_config["commands"]["stop"]

        click.echo("  -> Starting service for calibration...")
        run_command(start_cmd)
        time.sleep(10)  # Give it more time to be fully ready

        # Stage 1: Probe for the maximum achievable CPU utilization.
        # 阶段一：探测最大可达的CPU利用率。
        max_intensity = driver["intensity_variable"]["max"]
        click.secho(
            f"\n  [Probe] Testing with max intensity ({max_intensity}) "
            "to find CPU ceiling...",
            fg="cyan",
        )
        max_achievable_cpu = _run_benchmark_and_measure_cpu(
            driver["command_template"], max_intensity, duration=15
        )
        click.secho(
            f"  -> Maximum achievable CPU utilization: {max_achievable_cpu:.2f}%",
            fg="cyan",
        )

        if max_achievable_cpu < 1.0:
            click.secho(
                "❌ Error: Max achievable CPU is near zero. Cannot proceed.", fg="red"
            )
            run_command(stop_cmd)
            return

        # Stage 2: Calibrate each load level based on the max achievable CPU.
        # 阶段二：基于最大可达CPU，校准每一个负载等级。
        calibrated_intensities = {}
        load_levels = workload_config["target_load_levels"]

        for level_name, level_config in load_levels.items():
            target_min_pct = level_config["target_range"][0] / 100.0
            target_max_pct = level_config["target_range"][1] / 100.0
            dynamic_target_range = [
                max_achievable_cpu * target_min_pct,
                max_achievable_cpu * target_max_pct,
            ]

            click.echo(
                f"\n  -> Calibrating for '{level_name}' level..."
                f" Target CPU: [{dynamic_target_range[0]:.2f}%, "
                f"{dynamic_target_range[1]:.2f}%]"
            )

            # Binary Search Loop for the current level
            # 针对当前等级的二分查找循环
            low = driver["intensity_variable"]["min"]
            high = driver["intensity_variable"]["max"]
            optimal_intensity = None

            for i in range(7):  # More iterations for better precision
                if low > high:
                    break
                current_intensity = (low + high) // 2
                if current_intensity == 0:
                    current_intensity = 1  # Ensure intensity is at least 1

                click.echo(f"    [Iter {i+1}/7] Testing intensity: {current_intensity}")

                cpu_usage = _run_benchmark_and_measure_cpu(
                    driver["command_template"], current_intensity, duration=10
                )
                click.echo(f"    -> Observed CPU: {cpu_usage:.2f}%")

                if dynamic_target_range[0] <= cpu_usage <= dynamic_target_range[1]:
                    msg = (
                        f"    ✅ Target reached! Optimal intensity for "
                        f"'{level_name}': {current_intensity}"
                    )
                    click.secho(msg, fg="green")
                    optimal_intensity = current_intensity
                    break
                elif cpu_usage < dynamic_target_range[0]:
                    low = current_intensity + 1
                else:
                    high = current_intensity - 1

            if optimal_intensity is None:
                click.secho(
                    f"    ❌ Could not find optimal intensity for '{level_name}'.",
                    fg="yellow",
                )

            calibrated_intensities[level_name] = optimal_intensity

        click.echo("\n  -> Stopping service after calibration...")
        run_command(stop_cmd)

        # Stage 3: Generate the calibrated configuration file.
        # 阶段三：生成校准后的配置文件。
        if any(val is None for val in calibrated_intensities.values()):
            click.secho("❌ Calibration failed for one or more levels.", fg="red")
            click.echo(f"  -> Results: {calibrated_intensities}")
            return

        click.echo(f"  -> Generating calibrated config at {output_config}...")
        calibrated_config = {
            "workload_name": workload,
            "calibrated_parameters": {
                level: {"intensity": intensity}
                for level, intensity in calibrated_intensities.items()
            },
            "benchmark_driver": driver,
            "commands": workload_config["commands"],
        }

        try:
            with open(output_config, "w") as f:
                yaml.dump(
                    calibrated_config, f, default_flow_style=False, sort_keys=False
                )
            click.secho("✅ Successfully saved calibrated config!", fg="green")
        except IOError as e:
            click.secho(f"❌ Error saving config file: {e}", fg="red")

    except (ConfigError, ExecutionError) as e:
        click.secho(f"❌ Error: {e}", fg="red")
        return

    click.echo(f"🔧 Calibration finished. Config saved to: {output_config}")


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
