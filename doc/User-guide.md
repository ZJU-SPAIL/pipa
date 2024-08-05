# User Guide

This guide aims to clearly explain each step required for script generation and data processing, providing specific input examples to ensure users can correctly input the required parameters. The data processing section also includes instructions on how to use the PIPA tools to process and analyze performance data.

## Table of Contents

1. [Generating Data Collection Scripts](#generating-data-collection-scripts)
    - [Build Scripts that Collect Global Performance Data](#build-scripts-that-collect-global-performance-data)
    - [Build a Script that Collects Performance Data and Start the Workload by Perf](#build-a-script-that-collects-performance-data-and-start-the-workload-by-perf)
    - [Generate a Configuration Template for PIPA-SHU](#generate-a-configuration-template-for-pipa-shu)
        - [Default Configuration Explanation](#default-configuration-explanation)
        - [User Custom Options](#user-custom-options)
    - [Build Scripts Based on the Configuration File of PIPA-SHU](#build-scripts-based-on-the-configuration-file-of-pipa-shu)
    - [Generate a Configuration Template for PIPA-Upload](#generate-a-configuration-template-for-pipa-upload)
        - [Default Configuration Explanation](#default-configuration-explanation-1)
        - [User Custom Options](#user-custom-options-1)
    - [Exit](#exit)
2. [Export Current Server Hardware Information](#export-current-server-hardware-information)
3. [Generate pipa-upload Configuration Template](#generate-pipa-upload-configuration-template)
    - [Parameter Explanation](#parameter-explanation)
4. [Data Upload](#data-upload)
    - [Parameter Explanation](#parameter-explanation-1)

## Generating Data Collection Scripts

```shell
pipa generate
```

Using the above command will generate data collection scripts to assist in collecting performance data. The CLI provides several options:

```
"Build scripts that collect global performance data.",
"Build a script that collects performance data and start the workload by perf.",
"Generate a configuration template configuration of PIPA-SHU.",
"Build scripts based on the configuration file of PIPA-SHU.",
"Generate a configuration template configuration of pipa-upload.",
"Exit."
```

PIPA can generate shell scripts to assist in data collection. It mainly provides options for CLI input script configuration and generating scripts through YAML configuration files. The following explains the function of each option.

### Build Scripts that Collect Global Performance Data

Generates a `perf` global performance data collection script. Through the command line, the user can specify the following options: workspace path (`workspace`), frequency record (`freq_record`), event record (`events_record`), frequency statistics (`freq_stat`), event statistics (`events_stat`), whether to use `perf-annotate` (`annotate: True` or `False`), whether to use `taskset` to bind the process to specific cores (`use_taskset`), if using `taskset`, specify the core range (`core_range`), and the workload command (`command`).

### Build a Script that Collects Performance Data and Start the Workload by Perf

Generates a `perf` performance data collection script for the specified `workload` and automatically starts the `workload`, using the `ps` tool to collect the current CPU snapshot, and the `sar` tool to record global CPU usage, generating related hardware configuration files. Through the command line, the user can specify the following options: workspace path (`workspace`), frequency record (`freq_record`), event record (`events_record`), frequency statistics (`freq_stat`), event statistics (`events_stat`), whether to use `perf-annotate` (`annotate: True` or `False`), whether to use `taskset` to bind the process to specific cores (`use_taskset`), if using `taskset`, specify the core range (`core_range`), and the workload command (`command`).

### Generate a Configuration Template for PIPA-SHU

Generates a PIPA-SHU configuration template.

#### Default Configuration Explanation

The PIPA-SHU configuration template default configuration is as follows: the workspace path is `./data`, used to store performance data and collection scripts; the sampling frequency for `perf-record` is `999`, and the events used are `{cycles,instructions}:S`; whether to annotate performance data is `False`; whether to use `emon` is `True`; the statistics increment for `perf-stat` is `1000`, and the events used include `cycles`, `instructions`, `branch-misses`, `L1-dcache-load-misses`, and `L1-icache-load-misses`; the path for MPP is `/mnt/hdd/share/emon/system_health_monitor`; whether to run the workload through `perf` is `False`; the durations for `perf-record` and `perf-stat` are both `120` seconds, if set to `-1`, it runs until the workload completes or is manually terminated; whether to use `taskset` to bind the process to specific cores is `True`, using the core range `0-7`; the workload command is `perf bench futex hash`; whether to export the configuration after parsing is `True`.

#### User Custom Options

Users can modify this YAML configuration file according to actual needs to specify personalized parameters: users can customize the workspace path (`workspace`), adjust the sampling frequency for `perf-record` (`freq_record`) and the events used (`events_record`), choose whether to annotate performance data (`annotate`), decide whether to use `emon` (`use_emon`), adjust the statistics increment for `perf-stat` (`count_delta_stat`) and the events used (`events_stat`), specify the actual MPP path (`MPP_HOME`), decide whether to run the workload through `perf` (`run_by_perf`), set the durations for `perf-record` and `perf-stat` (`duration_record` and `duration_stat`), choose whether to use `taskset` to bind the process to specific cores (`use_taskset`), adjust the core range (`core_range`), and the workload command (`command`). Additionally, users can choose whether to export the configuration after parsing (`export_config`). Through these custom options, users can adjust the configuration according to specific needs and environments to correctly generate data collection scripts and run workloads.

### Build Scripts Based on the Configuration File of PIPA-SHU

Generates data collection and analysis scripts based on the PIPA-SHU configuration file. Note that the generated data collection scripts are global, please ensure the workload is started before running the generated `pipa-collect.sh` to collect data, and use `pipa-parse.sh` for data analysis after the data collection is complete. The default collection time in the configuration file is 120 seconds; if modification is needed, please adjust `duration_record` and `duration_stat` in the configuration file.

### Generate a Configuration Template for PIPA-Upload

Generates a PIPA-Upload configuration template.

#### Default Configuration Explanation

The PIPA-Upload configuration template default configuration is as follows: the workload name is `rocksdb`, the number of transactions is `7561946`, the data location is `/path/to/data/collected/by/pipashu`, the logical core numbers used are `[36, 37, 38, 39]`, the disk device name is `sdc`, the hardware configuration is `1*4*1` (sockets*cores*SMT), the software configuration is `RocksDB 7.9.2 build in release mode, debug_level=0, threads_num=16, db_bench with benchmark.sh`, the platform used is `Intel SPR 4510`, the CPU frequency is `2600 MHz` (when the platform is Huawei), the comment is `"This is a template for the upload configuration."`, the PIPAD server address is `10.82.77.113`, and the PIPAD server port is `50051`.

#### User Custom Options

Users can modify this YAML configuration file according to actual needs to specify personalized parameters: users can customize the workload name (`workload`), adjust the number of transactions (`transaction`), specify the actual data path (`data_location`), modify the actual logical core numbers used (`cores`), change the actual disk device name (`dev`), adjust `hw_info` according to actual hardware configuration, adjust `sw_info` according to the actual software version and configuration, modify the actual platform name (`platform`), provide the actual CPU frequency when the platform is Huawei (`cpu_frequency_mhz`), add related descriptions or remarks in the comment (`comment`), specify the actual PIPAD server address (`pipad_addr`) and port (`pipad_port`). Through these custom options, users can adjust the upload configuration according to specific needs and environments to correctly upload performance data to the PIPAD server.

### Exit

Exit the current `pipa generate` command line interface.

## Export Current Server Hardware Information

```shell
pipa export
```

This command outputs the current server's hardware information, including the operating system version, CPU model, memory size, disk size, network interface information, etc. The information is generated in the `./data/config/config` directory, with the files and corresponding information as follows:

- `dmidecode.txt`: Contains system hardware information obtained through the `dmidecode` command (requires root privileges).
- `pci_devices.txt`: Contains PCI device information obtained through the `lspci` command.
- `usb_devices.txt`: Contains USB device information obtained through the `lsusb` command.
- `block_devices.txt`: Contains block device information obtained through the `lsblk` command.
- `hardware.txt`: Contains detailed hardware information obtained through the `lshw` command.
- `cpu.txt`: Contains CPU information obtained through the `lscpu` command.
- `cpu-extended.txt`: Contains extended CPU information obtained through the `lscpu -a --extended` command.
- `modules.txt`: Contains kernel module information obtained through the `lsmod` command.
- `initrd.txt`: Contains initrd information obtained through the `lsinitrd` command.
- `ip.txt`: Contains network interface information obtained through the `ip addr` command.
- `disk_usage.txt`: Contains disk usage information obtained through the `df -h` command.
- `meminfo.txt`: Contains memory information obtained from the `/proc/meminfo` file.
- `cpuinfo.txt`: Contains CPU information obtained from the `/proc/cpuinfo` file.
- `perf-list.txt`: Contains performance events list obtained through the `perf list` command.
- `ulimit.txt`: Contains ulimit information obtained through the `ulimit -a` command.

Note, the number of files generated may vary due to the following reasons:

- `dmidecode.txt` requires root privileges to be generated.
- Some commands may not exist or be executable on the current system (e.g., `lsusb`, `lshw`, `lsinitrd`, etc.).
- Script execution may encounter errors or interruptions, resulting in some files not being generated.

## Generate pipa-upload Configuration Template

```shell
pipa dump /path/to/config.yaml --config_path ./config/settings.json --verbose
```

This command is similar to using the `pipa generate` command to generate configuration files. Each indicator is prompted by the CLI, and the user makes selections. Finally, the configuration is written to the specified YAML file based on the user's selections.

### Parameter Explanation

- **OUTPUT_PATH (`./data/test.yaml`)**:
  - **Type**: `str`
  - **Description**: A required parameter used to specify the location to export the data. In this example, the exported information will be saved in the `./data/test.yaml` file.

- **Optional Flags**:
  - **`--config_path` (`./config/settings.json`)**:
    - **Short Form**: `-c`
    - **Type**: `Optional[str]`
    - **Default**: `None`
    - **Description**: Specifies the path to a configuration file. In this example, `./config/settings.json` is used as the configuration file.
    
  - **`--verbose`**:
    - **Short Form**: `-v`
    - **Type**: `bool`
    - **Default**: `False`
    - **Description**: Enables verbose mode, providing more execution information. In this example, verbose mode is enabled.

## Data Upload

```shell
pipa upload /path/to/config.yaml --verbose
```

This command extracts and analyzes the relevant data specified in the YAML configuration file (it is recommended to use scripts generated by `pipa generate` to collect related data) and uploads it to the PIPAD server. If no configuration file is specified, the CLI will prompt for inputs, similar to the process of the `pipa dump` command. For more details, see the [Generate pipa-upload Configuration Template](#generate-pipa-upload-configuration-template) section.

### Parameter Explanation

- **Configuration File Path (`/path/to/config.yaml`)**:
  - **Type**: `str`
  - **Description**: A required parameter used to specify the path to the configuration file. In this example, the configuration file is located at `/path/to/config.yaml`.

- **Optional Flags**:
  - **`--verbose`**:
    - **Short Form**: `-v`
    - **Type**: `bool`
    - **Default**: `False`
    - **Description**: Enables verbose mode, providing more execution information. In this example, verbose mode is enabled.