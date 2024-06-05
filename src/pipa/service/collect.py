import os
from pipa.common.cmd import run_command
from pipa.common.config import DUMP_DIR
from pipa.common.utils import get_timestamp
from pipa.service.init import create_directories

create_directories()

def collect_perf_record(
    workload_cmd="perf bench futex hash",
    frequency=97,
    script_path=None,
    events="instructions,ref-cycles,cpu-cycles,branch-instructions,branch-misses",
):
    """
    Collects performance data using the 'perf' command.

    Args:
        workload_cmd (str, optional): The command to execute for workload. Defaults to "perf bench futex hash".
        frequency (int, optional): The frequency at which to sample events. Defaults to 97.
        output_file (str, optional): The path to the output file. If not provided, a default file name will be generated. Defaults to None.
        events (str, optional): The events to record. Defaults to "instructions,ref-cycles,cpu-cycles,branch-instructions,branch-misses".
    """
    now = get_timestamp()
    if not script_path:
        script_path = os.path.join(
            DUMP_DIR, f"workload_{now}.log"
        )  # TODO rename to perf
    # Construct the command to record the CPU events
    run_command(
        f"perf record -e {events} -a -F {frequency} {workload_cmd} > {script_path}"
    )
    # Generate a performance report
    report_path = os.path.join(DUMP_DIR, f"perf_{now}.report")
    run_command(f"perf report --header > {report_path}")
    # Generate output of the perf script
    script_path = os.path.join(
        DUMP_DIR, f"perf_{now}.script"
    )
    run_command(f"perf script --header > {script_path}")
    os.rename("perf.data", f"{DUMP_DIR}/perf_{now}.data")
    return report_path, script_path


def collect_perf_stat(
    workload_cmd="perf bench futex hash",
    sample_rate=997,
    perf_stat_output_path=None,
    events="instructions,ref-cycles,cpu-cycles,branch-instructions,branch-misses",
    core_range="0-19",
):
    """
    Collects performance statistics using the 'perf stat' command.

    Args:
        workload_cmd (str, optional): The command to run for workload. Defaults to "perf bench futex hash".
        sample_rate (int, optional): The sample rate for collecting statistics. Defaults to 997.
        perf_stat_output_path (str, optional): The output path for the perf stat results. If not provided, a default path will be used.
        events (str, optional): The events to measure. Defaults to "instructions,ref-cycles,cpu-cycles,branch-instructions,branch-misses".
        core_range (str, optional): The range of CPU cores to use. Defaults to "0-19".

    Returns:
        str: The path to the perf stat output file.
    """
    now = get_timestamp()
    perf_stat_output_path = perf_stat_output_path or os.path.join(
        DUMP_DIR, f"perf_stat_{now}.csv"
    )
    command = f"perf stat -e {events} -C {core_range} -A -x , -I {sample_rate} -o {perf_stat_output_path} {workload_cmd}"
    run_command(command)
    return perf_stat_output_path


def collect_perf_stat_with_sar(
    workload_cmd="perf bench futex hash",
    sample_rate=1000,
    perf_stat_output_path=None,
    sar_output_path=None,
    events="instructions,ref-cycles,cpu-cycles,branch-instructions,branch-misses",
    core_range="0-19",
):
    """
    Collects performance statistics using perf stat and sar commands.

    Args:
        workload_cmd (str, optional): Command to run for workload. Defaults to "perf bench futex hash".
        sample_rate (int, optional): Sampling rate in milliseconds. Defaults to 1000.
        perf_stat_output_path (str, optional): Path to save perf stat output. Defaults to None.
        sar_output_path (str, optional): Path to save sar output. Defaults to None.
        events (str, optional): Comma-separated list of events to monitor. Defaults to "instructions,ref-cycles,cpu-cycles,branch-instructions,branch-misses".
        core_range (str, optional): Range of CPU cores to monitor. Defaults to "0-19".

    Returns:
        Tuple[str, str]: Path to perf stat output file and path to sar output file.
    """
    sar_output_path = sar_output_path or f"data/dump/sar_output_{get_timestamp()}.dat"
    run_command(f"sar -o {sar_output_path} 1 >/dev/null 2>&1 &")
    perf_stat_output_path = collect_perf_stat(
        workload_cmd, sample_rate, perf_stat_output_path, events, core_range
    )
    run_command("killall sar")
    return perf_stat_output_path, sar_output_path


if __name__ == "__main__":
    collect_perf_stat_with_sar()
    collect_perf_record()
