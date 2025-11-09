import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from src.executor import ExecutionError
from src.utils import get_project_root

log = logging.getLogger(__name__)

# --- 直接引用内部的 flamegraph.pl 脚本 ---
PROJECT_ROOT = get_project_root()
FLAMEGRAPH_SCRIPT_PATH = PROJECT_ROOT / "third_party" / "FlameGraph" / "flamegraph.pl"


def _ensure_flamegraph_script_is_available() -> Path:
    """
    检查内部的 flamegraph.pl 脚本是否存在且可执行。
    """
    if not FLAMEGRAPH_SCRIPT_PATH.is_file():
        raise FileNotFoundError(
            f"Flamegraph script not found at the expected internal path: {FLAMEGRAPH_SCRIPT_PATH}\n"
            "Please ensure the FlameGraph repository is cloned into the 'third_party' directory."
        )
    FLAMEGRAPH_SCRIPT_PATH.chmod(0o755)
    return FLAMEGRAPH_SCRIPT_PATH


def generate_flamegraph_from_snapshot(snapshot_path: Path, output_svg_path: Path):
    """
    从 .pipa 快照生成火焰图 SVG 文件的核心引擎。
    """
    flamegraph_script = _ensure_flamegraph_script_is_available()

    with tempfile.TemporaryDirectory(prefix="pipa_flamegraph_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        log.info(f"Unpacking snapshot '{snapshot_path.name}' into temporary directory...")
        shutil.unpack_archive(snapshot_path, temp_dir, format="gztar")

        perf_data_path = temp_dir / "attach_session" / "perf.data"
        if not perf_data_path.exists():
            raise FileNotFoundError(
                "perf.data not found in the snapshot. " "Was the snapshot captured without the '--no-record' flag?"
            )

        log.info("Processing perf.data with `perf script`...")
        try:
            stackcollapse_script = PROJECT_ROOT / "third_party" / "FlameGraph" / "stackcollapse-perf.pl"
            if not stackcollapse_script.is_file():
                raise FileNotFoundError(f"stackcollapse-perf.pl not found at {stackcollapse_script}")
            stackcollapse_script.chmod(0o755)

            log.info("Running perf script...")
            perf_script_cmd = [
                "perf",
                "script",
                "-i",
                str(perf_data_path),
            ]
            perf_script_proc = subprocess.Popen(
                perf_script_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            log.info("Collapsing stacks with stackcollapse-perf.pl...")
            stackcollapse_cmd = ["perl", str(stackcollapse_script)]
            stackcollapse_proc = subprocess.Popen(
                stackcollapse_cmd,
                stdin=perf_script_proc.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            if perf_script_proc.stdout:
                perf_script_proc.stdout.close()

            log.info("Generating flame graph...")
            flamegraph_cmd = [str(flamegraph_script), "--color=hot", "--countname=samples"]
            flamegraph_proc = subprocess.Popen(
                flamegraph_cmd,
                stdin=stackcollapse_proc.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            if stackcollapse_proc.stdout:
                stackcollapse_proc.stdout.close()

            svg_content, fg_stderr = flamegraph_proc.communicate()

            perf_ret = perf_script_proc.wait()
            stackcollapse_ret = stackcollapse_proc.wait()

            if perf_ret != 0:
                _, perf_stderr = perf_script_proc.communicate()
                log.warning(f"perf script exited with code {perf_ret}: {perf_stderr}")

            if stackcollapse_ret != 0:
                _, stackcollapse_stderr = stackcollapse_proc.communicate()
                log.warning(f"stackcollapse-perf.pl exited with code {stackcollapse_ret}: {stackcollapse_stderr}")

            if flamegraph_proc.returncode != 0:
                raise ExecutionError(f"flamegraph.pl failed with error: {fg_stderr}")

            with open(output_svg_path, "w") as f:
                f.write(svg_content)
            log.info("Flame Graph SVG content successfully generated.")

        except FileNotFoundError as e:
            raise ExecutionError(f"Command not found: {e.filename}. Is 'perf' installed and in your PATH?")
        except Exception as e:
            log.error(f"An unexpected error occurred during flamegraph generation: {e}")
            raise
