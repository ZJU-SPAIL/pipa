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
        # --- Simulation of the workflow ---
        # --- 工作流模拟 ---
        click.echo("🚀 Starting adaptive calibration process...")

        driver = workload_config["benchmark_driver"]
        start_cmd = workload_config["commands"]["start"]
        stop_cmd = workload_config["commands"]["stop"]

        # 1. Start the service (once for the whole calibration)
        click.echo("  -> Starting service for calibration...")
        run_command(start_cmd)
        time.sleep(1)  # Give it more time to be fully ready

        # --- Binary Search Loop ---
        low = driver["intensity_variable"]["min"]
        high = driver["intensity_variable"]["max"]
        target_range = workload_config["target_load_levels"]["medium"]["target_range"]
        optimal_intensity = None

        click.echo(
            f"  -> Searching for intensity to reach target CPU of {target_range}%..."
        )

        # We'll do a few iterations of binary search
        for i in range(5):  # Limit to 5 iterations to avoid infinite loops
            if low > high:
                break

            current_intensity = (low + high) // 2
            if current_intensity == 0:  # Avoid getting stuck
                break

            click.echo(
                f"\n  [Iteration {i+1}/5] Testing with intensity: {current_intensity}"
            )

            benchmark_cmd = driver["command_template"].format(
                intensity=current_intensity
            )
            benchmark_proc = run_in_background(benchmark_cmd)

            # Give benchmark a moment to ramp up
            time.sleep(5)

            # --- This is the core feedback loop! ---
            # --- 这是核心的反馈循环！ ---
            try:
                cpu_usage = collect_cpu_utilization(duration=15)
                click.echo(f"  -> Observed CPU utilization: {cpu_usage:.2f}%")

                if target_range[0] <= cpu_usage <= target_range[1]:
                    msg = (
                        f"  ✅ Target reached! "
                        f"Optimal intensity found: {current_intensity}"
                    )
                    click.secho(msg, fg="green")
                    optimal_intensity = current_intensity
                    benchmark_proc.terminate()
                    break
                elif cpu_usage < target_range[0]:
                    click.echo("  -> CPU usage is too low. Increasing intensity.")
                    low = current_intensity + 1
                else:  # cpu_usage > target_range[1]
                    click.echo("  -> CPU usage is too high. Decreasing intensity.")
                    high = current_intensity - 1

            finally:
                # Always ensure the benchmark process is stopped
                # 总是确保压测进程被停止
                if benchmark_proc.poll() is None:
                    benchmark_proc.terminate()
                    benchmark_proc.wait(timeout=5)

        # 5. Stop the service
        click.echo("\n  -> Stopping service after calibration...")
        run_command(stop_cmd)

        if optimal_intensity is None:
            click.secho("❌ Calibration failed...", fg="red")
        else:
            # **--- Generate the calibrated YAML file ---**
            click.echo(f"  -> Generating calibrated config at {output_config}...")

            # 推算 low 和 high 的强度
            # (我们可以让这个逻辑更智能，但现在先用简单的比例)
            low_intensity = max(
                driver["intensity_variable"]["min"], optimal_intensity // 4
            )
            high_intensity = min(
                driver["intensity_variable"]["max"], optimal_intensity * 2
            )

            calibrated_config = {
                "workload_name": workload,
                "calibrated_parameters": {
                    "low": {"intensity": low_intensity},
                    "medium": {"intensity": optimal_intensity},
                    "high": {"intensity": high_intensity},
                },
                "benchmark_driver": driver,  # 把原始驱动信息也存进去
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

    click.echo(f"🔧 Calibrated config saved to: {output_config}")

    click.echo("✅ Calibration finished (simulation).")


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
