import questionary
import os

config_template = """
workspace: ./data # The workspace to store the performance data and collecting script. Will be created if not exists.
freq_record: 999 # The frequency of perf-record.
events_record: "{cycles,instructions}:S" # The events to be used in perf-record.
annotete: False # Whether to annotate the performance data.

use_emon: False # Whether to use emon.

count_delta_stat: 1000 # The count delta of perf-stat.
# No need to set if use_emon is True.
events_stat: # The events to be used in perf-stat.
        - cycles
        - instructions
        - branch-misses
        - L1-dcache-load-misses
        - L1-icache-load-misses
# No need to set if use_emon is True.

MPP_HOME: /mnt/hdd/share/emon/system_health_monitor # The path to the mpp.
# No need to set if use_emon is False.

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

export_config: True # Whether to export the configuration after parsing.

"""


def write_config(config_file="config-pipa-shu.yaml"):
    with open(config_file, "w") as f:
        f.write(config_template)


def query_filepath():
    workspace = questionary.text(
        "Where do you want to store the configuration template? (Default: ./)\n", "./"
    ).ask()
    if workspace == "":
        workspace = "./"
    return workspace


def generate_template(filename: str):
    workspace = query_filepath()
    config_file_path = os.path.join(workspace, filename)
    if not os.path.exists(workspace):
        os.makedirs(workspace)
    return write_config(config_file_path)


def generate_pipashu_template():
    return generate_template("config-pipa-shu.yaml")


upload_template = """workload: rocksdb
# The name of the workload.
transaction: 7561946
# The number of transactions.
data_location: /path/to/data/collected/by/pipashu
# The location of the data collected by PIPAShu.
cores: [36, 37, 38, 39]
# The numbers of logical cores used in the workload.
dev: sdc
# The used disk device name.
hw_info: 1*4*1
# The hardware configuration (sockets*cores*SMT).
sw_info: RocksDB 7.9.2 build in release mode, debug_level=0, threads_num=16, db_bench with benchmark.sh
# The software configuration.
platform: Intel SPR 4510
# The platform user used.
comment: "This is a template for the upload configuration."
# Any comments.
pipad_addr: 10.82.77.113
# The PIPAD server address.
pipad_port: 50051
# The PIPAD server port.
"""


def generate_upload_template():
    return generate_template("config-upload.yaml")
