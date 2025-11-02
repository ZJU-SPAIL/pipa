import logging
import math
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
        time.sleep(10)

        min_intensity = driver["intensity_variable"]["min"]
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
            click.secho("❌ Error: Max CPU is near zero. Cannot proceed.", fg="red")
            run_command(stop_cmd)
            return

        click.echo(
            "\n  -> Starting Coarse-grained Scan to map performance landscape..."
        )
        performance_map = []
        num_steps = 12
        step_coarse = math.ceil((max_intensity - min_intensity + 1) / num_steps)
        step_coarse = max(1, step_coarse)

        for intensity in range(min_intensity, max_intensity + 1, step_coarse):
            click.echo(f"    [Coarse Scan] Testing intensity: {intensity}")
            cpu_usage = _run_benchmark_and_measure_cpu(
                driver["command_template"], intensity, duration=10
            )
            click.echo(f"    -> Observed CPU: {cpu_usage:.2f}%")
            performance_map.append({"intensity": intensity, "cpu": cpu_usage})

        if max_intensity not in [p["intensity"] for p in performance_map]:
            performance_map.append(
                {"intensity": max_intensity, "cpu": max_achievable_cpu}
            )

        click.echo("\n  -> Finding globally optimal monotonic triplet...")
        best_triplet = None
        min_total_distance = float("inf")
        load_levels = workload_config["target_load_levels"]

        targets = {
            name: (
                max_achievable_cpu * (conf["target_range"][0] / 100.0)
                + max_achievable_cpu * (conf["target_range"][1] / 100.0)
            )
            / 2
            for name, conf in load_levels.items()
        }

        for p_low in performance_map:
            for p_medium in performance_map:
                for p_high in performance_map:
                    if not (
                        p_low["intensity"] < p_medium["intensity"] < p_high["intensity"]
                        and p_low["cpu"] < p_medium["cpu"] < p_high["cpu"]
                    ):
                        continue

                    dist_low = abs(p_low["cpu"] - targets["low"])
                    dist_medium = abs(p_medium["cpu"] - targets["medium"])
                    dist_high = abs(p_high["cpu"] - targets["high"])
                    total_distance = dist_low + dist_medium + dist_high

                    if total_distance < min_total_distance:
                        min_total_distance = total_distance
                        best_triplet = {
                            "low": p_low,
                            "medium": p_medium,
                            "high": p_high,
                        }

        if best_triplet is None:
            click.secho("❌ Could not find a monotonic performance path.", fg="red")
            run_command(stop_cmd)
            return

        click.secho("  -> Found optimal coarse points:", fg="green")
        for name, point in best_triplet.items():
            click.echo(
                f"    - {name}: intensity={point['intensity']}, cpu={point['cpu']:.2f}%"
            )

        calibrated_intensities = {}
        last_intensity = 0
        last_cpu = 0.0

        level_order = ["low", "medium", "high"]
        for i, level_name in enumerate(level_order):
            coarse_point = best_triplet[level_name]

            # --- 最终修复：约束搜索范围，使其互不重叠 ---
            search_min = max(
                last_intensity + 1, coarse_point["intensity"] - step_coarse // 2
            )

            # 下一个等级的粗粒度强度，是当前等级搜索的“天花板”
            if i + 1 < len(level_order):
                next_level_coarse_intensity = best_triplet[level_order[i + 1]][
                    "intensity"
                ]
                search_max = min(
                    max_intensity,
                    coarse_point["intensity"] + step_coarse // 2,
                    next_level_coarse_intensity - 1,
                )
            else:
                search_max = min(
                    max_intensity, coarse_point["intensity"] + step_coarse // 2
                )

            # Ensure min is not greater than max
            search_min = min(search_min, search_max)

            click.echo(
                f"\n  -> Fine-tuning for '{level_name}' "
                f"in range [{search_min}, {search_max}]..."
            )

            best_point = None
            min_distance = float("inf")

            for intensity in range(search_min, search_max + 1):
                click.echo(f"    [Fine Scan] Testing intensity: {intensity}")
                cpu_usage = _run_benchmark_and_measure_cpu(
                    driver["command_template"], intensity, duration=10
                )
                click.echo(f"    -> Observed CPU: {cpu_usage:.2f}%")

                if cpu_usage <= last_cpu:
                    continue

                distance = abs(cpu_usage - targets[level_name])
                if distance < min_distance:
                    min_distance = distance
                    best_point = {"intensity": intensity, "cpu": cpu_usage}

            if best_point:
                calibrated_intensities[level_name] = best_point["intensity"]
                last_intensity = best_point["intensity"]
                last_cpu = best_point["cpu"]
                click.secho(
                    f"  -> Best fine-tuned intensity for"
                    f" '{level_name}': {best_point['intensity']}",
                    fg="green",
                )
            else:
                click.secho(
                    f"  -> Could not fine-tune for '{level_name}', using coarse value.",
                    fg="yellow",
                )
                # Fallback to coarse point if no better point is found
                calibrated_intensities[level_name] = coarse_point["intensity"]
                last_intensity = coarse_point["intensity"]
                last_cpu = coarse_point["cpu"]

        click.echo("\n  -> Stopping service after calibration...")
        run_command(stop_cmd)

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
