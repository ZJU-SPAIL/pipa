import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

import click

from src.executor import ExecutionError
from src.utils import get_project_root

log = logging.getLogger(__name__)

PROJECT_ROOT = get_project_root()
FLAMEGRAPH_SCRIPT_PATH = PROJECT_ROOT / "third_party" / "FlameGraph" / "flamegraph.pl"


def _ensure_flamegraph_script_is_available() -> Path:
    if not FLAMEGRAPH_SCRIPT_PATH.is_file():
        raise FileNotFoundError(
            f"Flamegraph script not found: {FLAMEGRAPH_SCRIPT_PATH}. " "Ensure submodule is initialized."
        )
    FLAMEGRAPH_SCRIPT_PATH.chmod(0o755)
    return FLAMEGRAPH_SCRIPT_PATH


def _generate_flamegraph_from_snapshot(snapshot_path: Path, output_svg_path: Path):
    flamegraph_script = _ensure_flamegraph_script_is_available()

    with tempfile.TemporaryDirectory(prefix="pipa_flamegraph_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        log.info(f"Unpacking snapshot '{snapshot_path.name}'...")
        shutil.unpack_archive(snapshot_path, temp_dir, format="gztar")

        perf_data_path = next(temp_dir.rglob("perf.data"), None)
        if not perf_data_path:
            raise FileNotFoundError("perf.data not found in snapshot.")

        log.info("Processing perf.data with `perf script`...")
        try:
            stackcollapse_script = PROJECT_ROOT / "third_party" / "FlameGraph" / "stackcollapse-perf.pl"
            if not stackcollapse_script.is_file():
                raise FileNotFoundError(f"stackcollapse-perf.pl not found at {stackcollapse_script}")
            stackcollapse_script.chmod(0o755)

            perf_script_proc = subprocess.Popen(
                ["perf", "script", "-i", str(perf_data_path)], stdout=subprocess.PIPE, text=True
            )
            stackcollapse_proc = subprocess.Popen(
                ["perl", str(stackcollapse_script)], stdin=perf_script_proc.stdout, stdout=subprocess.PIPE, text=True
            )
            if perf_script_proc.stdout:
                perf_script_proc.stdout.close()

            flamegraph_proc = subprocess.Popen(
                [str(flamegraph_script), "--color=hot", "--countname=samples"],
                stdin=stackcollapse_proc.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if stackcollapse_proc.stdout:
                stackcollapse_proc.stdout.close()

            svg_content, fg_stderr = flamegraph_proc.communicate()

            if flamegraph_proc.returncode != 0:
                raise ExecutionError(f"flamegraph.pl failed: {fg_stderr}")

            with open(output_svg_path, "w") as f:
                f.write(svg_content)
            log.info("Flame Graph SVG content successfully generated.")

        except FileNotFoundError as e:
            raise ExecutionError(f"Command not found: {e.filename}. Is 'perf' or 'perl' installed?")
        except Exception as e:
            log.error(f"An unexpected error during flamegraph generation: {e}")
            raise


@click.command()
@click.option(
    "--input",
    "input_path_str",
    required=True,
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to the .pipa archive containing perf.data.",
)
@click.option(
    "--output",
    "output_path_str",
    required=True,
    type=click.Path(writable=True, dir_okay=False, resolve_path=True),
    help="Path to save the generated Flame Graph SVG file.",
)
def flamegraph(input_path_str: str, output_path_str: str):
    """
    从 .pipa 快照生成交互式火焰图 (SVG)。
    """
    input_path = Path(input_path_str)
    output_path = Path(output_path_str)

    try:
        click.echo(f"🔥 Generating Flame Graph from '{input_path.name}'...")
        _generate_flamegraph_from_snapshot(input_path, output_path)
        click.secho(f"✅ Flame Graph successfully saved to: {output_path}", fg="green")
    except Exception as e:
        click.secho(f"❌ An error occurred during Flame Graph generation: {e}", fg="red")
        raise click.Abort()
