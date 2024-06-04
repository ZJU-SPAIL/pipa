# Quick Start

This guide will walk you through the installation process and basic usage of the pipa package.

## Installation

1. Connect to the black server.
2. Open a terminal or command prompt.
3. Use the following command to install the package:
    ```shell
    pip install /mnt/hdd/share/pipa-*.whl
    ```

## Usage

To use the pipa package, follow these steps:

1. Import the run_and_collect_all function from the pipa.service module:
    ```python
    from pipa.service.run import run_and_collect_all
    ```
2. Call the run_and_collect_all function with the desired command as a string parameter. For example, let's use the command "perf bench futex hash":
    ```python
    sar_df_list, perf_stat_df, perf_script_df = run_and_collect_all("perf bench futex hash")
    ```
    The function will execute the command and collect the performance data.  
    The collected data will be returned as three separate dataframes: `sar_df_list`, `perf_stat_df`, and `perf_script_df`.

Feel free to explore the pipa package further to leverage its additional features and functionalities.
