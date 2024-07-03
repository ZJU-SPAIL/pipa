# User Guide
This guide aims to clearly explain each step required for script generation and data processing, providing specific input examples to ensure users can correctly input the required parameters. The data processing section also includes instructions on how to use the PIPA tools to process and analyze performance data.

## Table of Contents

- [Script Generation](#script-generation)
  - [Run by PIPA](#run-by-pipa)
  - [Run by User](#run-by-user)
- [Data Processing](#data-processing)
  - [Parsing SAR Data](#parsing-sar-data)
  - [Parsing perf Script Files](#parsing-perf-script-files)
  - [Parsing perf Report Files](#parsing-perf-report-files)
  - [Parsing perf Stat Files](#parsing-perf-stat-files)
- [Data Visualization](#data-visualization)
- [Data Analytics](#data-analytics)

## Script Generation

After installation, you can start using PIPA to collect, integrate, and analyze your data.

To generate a script that collects performance data, use the following command:

```sh
pipa generate
```

### Run by PIPA

If you select `Build a script that collects performance data and start the workload by perf.`, you will be prompted to answer several questions via the command-line interface. These questions help configure the script:

1. **Data Storage Path**:
   - Specify the directory where the collected data should be stored.
   - Example input: `/path/to/your/workspace`

2. **Frequency and Events of `perf-record`**:
   - Frequency (in Hz) for recording performance events.
   - Example input: `1000`
   - Events to record, separated by commas.
   - Example input: `cycles,instructions,cache-misses`

3. **Frequency and Events of `perf-stat`**:
   - Frequency (in Hz) for collecting performance statistics.
   - Example input: `1000`
   - Events to stat, separated by commas.
   - Example input: `cycles,instructions,cache-misses`

4. **Use `perf-annotate`**:
   - Choose whether to use `perf-annotate` to annotate the collected data.
   - Example input: `Yes` or `No`

5. **Set the Duration of `perf-record` and `perf-stat`**:
   - Choose whether to set a specific duration for `perf-record` and `perf-stat`.
   - Example input: `Yes` or `No, I'll control it by myself. (Exit by Ctrl+C)`
   - If `Yes`, specify the duration in seconds.
   - Example input: `10`

After providing these inputs, PIPA will generate a script named `pipa-collect.sh`. Run this script to start collecting global performance data:

```sh
sh /path/to/your/workspace/pipa-collect.sh
```

### Run by User

If you select `Build a script that collects global performance data.`, you will be prompted to answer several questions via the command-line interface. These questions help configure the script:

1. **Data Storage Path**:
   - Specify the directory where the collected data should be stored.
   - Example input: `/path/to/your/workspace`

2. **Frequency and Events of `perf-record`**:
   - Frequency (in Hz) for recording performance events.
   - Example input: `1000`
   - Events to record, separated by commas.
   - Example input: `cycles,instructions,cache-misses`

3. **Frequency and Events of `perf-stat`**:
   - Frequency (in Hz) for collecting performance statistics.
   - Example input: `1000`
   - Events to stat, separated by commas.
   - Example input: `cycles,instructions,cache-misses`

4. **Use `perf-annotate`**:
   - Choose whether to use `perf-annotate` to annotate the collected data.
   - Example input: `Yes` or `No`

5. **Use `taskset`**:
   - Choose whether to bind the workload to specific CPU cores using `taskset`.
   - Example input: `Yes` or `No`
   - If `Yes`, specify the core range.
   - Example input: `120-140`

6. **Workload Command**:
   - Specify the command that starts the workload you want to analyze.
   - Example input: `perf bench futex hash`

After providing these inputs, PIPA will generate a script named `pipa-run.sh`. Run this script to start the workload with `perf` and collect performance data:

```sh
sh /path/to/your/workspace/pipa-run.sh
```

## Data Processing

After collecting performance data, you can use PIPA to process and analyze this data. PIPA provides several tools for parsing and analyzing performance data, including `SarData`, `perf_script.py`, `perf_report.py`, and `perf_stat.py`.

### Parsing SAR Data

1. **Initialize `SarData` object**:
   - Initialize the `SarData` object using a SAR text file or binary file.
   ```python
   from pipa.parser.sar import SarData

   # Using a SAR text file
   sar_data = SarData.init_with_sar_txt("/path/to/your/sar.txt")

   # Using a SAR binary file
   sar_data = SarData.init_with_sar_bin("/path/to/your/sar.bin")
   ```

2. **Get CPU Utilization**:
   - Retrieve detailed CPU utilization data and plot the chart.
   ```python
   cpu_utilization = sar_data.get_CPU_utilization(data_type="detail")
   sar_data.plot_CPU_util_time(threads=[0, 1, 2, 3])
   ```

3. **Get Memory Usage**:
   - Retrieve detailed memory usage data and plot the chart.
   ```python
   memory_usage = sar_data.get_memory_usage(data_type="detail")
   sar_data.plot_memory_usage()
   ```

### Parsing `perf` Script Files

1. **Prepare `perf` script file**:
   - Ensure you have generated a `perf` script file containing performance data. For example, the file path might be `/path/to/perf.script`.

2. **Run the analysis tool**:
   - Execute the following command to start the analysis tool:
     ```sh
     python perf_script.py
     ```
   - The tool will prompt you to input the path to the `perf` script file:
     ```plaintext
     input perf script text data path:
     ```
   - Enter the path to the `perf` script file and press Enter, for example:
     ```plaintext
     /path/to/perf.script
     ```

3. **Parsing Results**:
   - The tool will parse the specified `perf` script file and convert the parsed data into a pandas DataFrame.

### Parsing `perf` Report Files

1. **Prepare `perf` report file**:
   - Ensure you have generated a `perf` report file containing performance data. For example, the file path might be `/path/to/perf.report`.

2. **Run the analysis tool**:
   - Execute the following command to start the analysis tool:
     ```sh
     python perf_report.py
     ```
   - The tool will prompt you to input the path to the `perf` report file:
     ```plaintext
     input perf report text data path:
     ```
   - Enter the path to the `perf` report file and press Enter, for example:
     ```plaintext
     /path/to/perf.report
     ```

3. **Parsing Results**:
   - The tool will parse the specified `perf` report file and convert the parsed data into a pandas DataFrame.

### Parsing `perf` Stat Files

1. **Prepare `perf` stat file**:
   - Ensure you have generated a `perf` stat file containing performance data. For example, the file path might be `/path/to/perf_stat.csv`.

2. **Run the analysis tool**:
   - Initialize and use the `PerfStatData` class to parse the `perf` stat file:
   ```python
   from pipa.parser.perf_stat import PerfStatData

   # Initialize PerfStatData object
   perf_stat_data = PerfStatData("/path/to/perf_stat.csv")

   # Get CPI data
   cpi_data = perf_stat_data.get_CPI()
   print(cpi_data)

   # Plot CPI over time for specific threads
   perf_stat_data.plot_CPI_time_by_thread(threads=[0, 1, 2, 3])

   # Plot CPI over time for the system
   perf_stat_data.plot_CPI_time_system()
   ```

3. **Parsing Results**:
   - The `PerfStatData` class will parse the specified `perf` stat file and provide methods to analyze and visualize the CPI (Cycles Per Instruction) data.

By following these steps, you can use the `SarData` class and the `perf_script.py`, `perf_report.py`, and `perf_stat.py` tools provided by PIPA to process and analyze performance data, generating useful performance metrics charts to better understand system performance.

## Data Visualization

## Data Analytics
