import questionary
import os

config_template = """
workspace: ./data # The workspace to store the performance data and collecting script. Will be created if not exists.
freq_record: 999 # The frequency of perf-record.
events_record: "{cycles,instructions}:S" # The events to be used in perf-record.
count_delta_stat: 1000 # The count delta of perf-stat.
events_stat: # The events to be used in perf-stat.
        - cycles
        - instructions
        - branch-misses
        - L1-dcache-load-misses
        - L1-icache-load-misses
annotete: False # Whether to annotate the performance data.

run_by_perf: False # Whether to run the workload by perf.

duration_record: 120 # The duration of the perf-record.
# No need to set if run_by_perf is True.
# Set it -1 if you want to run the perf until workload finishes or you kill perf manually.
duration_stat: 120 # The duration of the perf-stat.
# No need to set if run_by_perf is True.
# Set it -1 if you want to run the perf until workload finishes or you kill perf manually.

use_taskset: True # Whether to use taskset to bind the process to specific cores.
# No need to set if run_by_perf is False.
core_range: 0-7 # The range of cores to be used.
# No need to set if use_taskset or run_by_perf is False.
command: perf bench futex hash # The command to run workload.
# No need to set if run_by_perf is False.

export_config: True # Whether to export the config files.

"""


def write_config(config_file="config-pipa-shu.yaml"):
    with open(config_file, "w") as f:
        f.write(config_template)


def generate_template():
    workspace = questionary.text(
        "Where do you want to store the configuration template? (Default: ./)\n", "./"
    ).ask()
    config_file_path = os.path.join(workspace, "config-pipa-shu.yaml")
    if not os.path.exists(workspace):
        os.makedirs(workspace)
    write_config(config_file_path)
