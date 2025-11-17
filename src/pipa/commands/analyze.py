import logging
import pprint
import shutil
import tempfile
from pathlib import Path

import click
import yaml
from markdown_it import MarkdownIt

from src.pipa.parsers import PARSER_REGISTRY
from src.pipa.report.context_builder import build_full_context
from src.pipa.report.html_generator import generate_html_report
from src.pipa.report.plotter import plot_sar_cpu, plot_timeseries_generic
from src.utils import get_project_root

from .rules import format_rules_to_html_tree, load_rules

log = logging.getLogger(__name__)


def _generate_report(level_dir: Path, report_path: Path):
    """
    Analyzes all available sampling data and generates a comprehensive HTML report.
    (This is the core engine logic, now internal to the analyze command).
    """
    log.info(f"--- Generating analysis report from directory: {level_dir} ---")
    analysis_warnings = []
    all_dataframes = {}

    static_info_str, static_info_data = "", {}
    try:
        static_info_path = level_dir.parent / "static_info.yaml"
        with open(static_info_path, "r") as f:
            static_info_data = yaml.safe_load(f)
            static_info_str = yaml.dump(static_info_data, indent=2, allow_unicode=True)
        log.info(f"Loaded static system info from {static_info_path.name}.")
    except FileNotFoundError:
        analysis_warnings.append("static_info.yaml not found. The report will lack system context.")

    log.info("Dynamically loading all data files using the parser registry...")

    files_to_parse = {
        "perf_stat.txt": "perf_stat",
        "sar_cpu.csv": "sar_cpu",
        "sar_network.csv": "sar_network",
        "sar_io.csv": "sar_io",
        "sar_memory.csv": "sar_memory",
        "sar_paging.csv": "sar_paging",
        "sar_load.csv": "sar_load",
    }

    for filename, registry_key in files_to_parse.items():
        file_path = level_dir / filename
        parser_func = PARSER_REGISTRY.get(registry_key)

        if not file_path.exists():
            if filename == "perf_stat.txt":
                analysis_warnings.append(f"{filename} not found. Perf-related analysis will be skipped.")
            continue
        if file_path.stat().st_size == 0:
            analysis_warnings.append(f"{filename} is empty.")
            continue

        if parser_func:
            try:
                if filename.endswith(".txt"):
                    content = file_path.read_text()
                    df = parser_func(content)
                else:
                    df = parser_func(file_path)

                if registry_key == "perf_stat":
                    all_dataframes["perf_raw"] = df
                else:
                    all_dataframes[registry_key] = df
                log.info(f"Successfully parsed {filename} using '{parser_func.__module__}'.")

            except Exception as e:
                log.warning(f"Failed to process {filename} with its parser: {e}", exc_info=True)
                analysis_warnings.append(f"Error parsing {filename}: {e}")
        else:
            log.warning(f"No parser registered for '{registry_key}', skipping file.")

    if not (level_dir / "perf.data").exists():
        analysis_warnings.append("perf.data not found. Flame graph generation will not be possible.")

    project_root = get_project_root()
    rules_path = project_root / "config/rules/decision_tree.yaml"
    rules, rule_configs = load_rules(rules_path)
    context = build_full_context(all_dataframes, static_info_data)
    context.update(rule_configs)

    log.debug("--- [DEBUG] Final Context for Decision Engine ---")
    log.debug(f"\n{pprint.pformat(context)}")
    log.debug("-------------------------------------------------")

    md = MarkdownIt()
    decision_tree_html, findings_for_tree_html = format_rules_to_html_tree(rules, all_dataframes, context, md)

    plots = {}
    tables = {}

    if "perf_raw" in all_dataframes and not all_dataframes["perf_raw"].empty:
        df_perf = (
            all_dataframes["perf_raw"]
            .pivot_table(index=["timestamp", "cpu"], columns="event_name", values="value")
            .reset_index()
        )
        all_dataframes["perf"] = df_perf

    for name, df in all_dataframes.items():
        if name == "perf_raw" or df.empty:
            continue

        log.info(f"Processing data for '{name}'...")
        tables[name] = df.round(2).to_json(orient="records")

        try:
            time_col = "timestamp"
            if time_col not in df.columns:
                continue

            if name == "sar_cpu":
                fig = plot_sar_cpu(df)
                plots[name] = fig.to_html(full_html=False, include_plotlyjs="cdn")

                metrics_to_plot = [m for m in ["%user", "%system", "%iowait", "%idle", "%total"] if m in df.columns]
                filter_options = {"CPU": sorted(df["CPU"].unique().tolist()), "METRIC": metrics_to_plot}
                filters_with_hints = {}
                for key, values in filter_options.items():
                    source_property = "legendgroup" if key == "CPU" else "name"
                    filters_with_hints[key] = {
                        "values": values,
                        "sample": values[:3],
                        "count": len(values),
                        "source": source_property,
                    }
                context[f"{name}_filters"] = filters_with_hints
            else:
                generated_plots, generated_filters = plot_timeseries_generic(df, name)
                for plot_name, fig in generated_plots.items():
                    plots[plot_name] = fig.to_html(full_html=False, include_plotlyjs="cdn")
                context.update(generated_filters)
        except Exception as e:
            log.warning(f"Could not generate plot for '{name}': {e}", exc_info=True)

    generate_html_report(
        output_path=report_path,
        md_instance=md,
        warnings=analysis_warnings,
        plots=plots,
        tables_json=tables,
        decision_tree_html=decision_tree_html,
        findings_for_tree_html=findings_for_tree_html,
        static_info_data=static_info_data,
        static_info_str=static_info_str,
        context=context,
    )


def _get_unique_output_path(base_path: Path) -> Path:
    """Generate a unique output file path by appending a number if the file exists."""
    if not base_path.exists():
        return base_path
    stem = base_path.stem
    suffix = base_path.suffix
    parent = base_path.parent
    counter = 1
    while True:
        new_name = f"{stem}_{counter}{suffix}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
        counter += 1


# --- 核心修改: 从 `commands_old/analyze.py` 移入的 CLI 定义 ---
@click.command()
@click.option(
    "--input",
    "input_path_str",
    required=True,
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to the .pipa archive to analyze.",
)
@click.option(
    "--output",
    "output_path_str",
    required=False,
    type=click.Path(writable=True, dir_okay=False, resolve_path=True),
    default=None,
    help="Path to save the generated HTML report. If not specified, generates 'report.html' in current directory.",
)
def analyze(input_path_str: str, output_path_str: str):
    """Analyzes sampling results and generates a comprehensive HTML report."""
    input_path = Path(input_path_str)

    if output_path_str is None:
        output_path = _get_unique_output_path(Path("report.html").resolve())
    else:
        output_path = Path(output_path_str)
        if output_path.exists():
            output_path = _get_unique_output_path(output_path)

    with tempfile.TemporaryDirectory(prefix="pipa_analyze_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        click.echo(f"Unpacking archive '{input_path.name}' for analysis...")
        shutil.unpack_archive(input_path, temp_dir, format="gztar")

        level_dir = None
        unpacked_items = list(temp_dir.iterdir())
        if len(unpacked_items) == 1 and unpacked_items[0].is_dir():
            level_dir = unpacked_items[0]
        else:
            for item in unpacked_items:
                if item.is_dir() and item.name.startswith("attach_session"):
                    level_dir = item
                    break

        if not level_dir:
            click.secho("Error: No valid data directory found in the archive.", fg="red")
            raise click.Abort()

        try:
            _generate_report(level_dir, output_path)
            click.secho(f"\n✅ Analysis complete. Report saved to: {output_path}", fg="green")
        except Exception as e:
            click.secho(f"❌ An error occurred during report generation: {e}", fg="red")
            raise click.Abort()
