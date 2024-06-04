# API reference

## export configuration

```py
def get_all_config():
    """
    Retrieves all configuration information.

    This function calls several other functions to gather platform information,
    system configuration, and CPU configuration.

    Returns:
        None
    """
```

usage:

```py
from pipa.export_config.all import get_all_config

get_all_config()
```


## parse

### sar

```py
def parse_sar_all(sar_bin_path: str):
    """
    Parses the SAR binary file and returns a list of dataframes.

    Args:
        sar_bin_path (str): The path to the SAR binary file.

    Returns:
        List[pd.DataFrame]: A list of dataframes containing the parsed SAR data.
    """
```

usage:

```py
from pipa.parser.sar import parse_sar_all
sar_df_list  = parse_sar_all(sar_bin_path)
```

### perf stat

```py
def parse_perf_stat_file(stat_output_path: str):
    """
    Parse the perf stat output file and return a pandas DataFrame.

    Args:
        stat_output_path (str): The path to the perf stat output file.

    Returns:
        pandas.DataFrame: The parsed data as a DataFrame.

    The fields are in this order:
    •   optional usec time stamp in fractions of second (with -I xxx)
    •   optional CPU, core, or socket identifier
    •   optional number of logical CPUs aggregated
    •   counter value
    •   unit of the counter value or empty
    •   event name
    •   run time of counter
    •   percentage of measurement time the counter was running
    •   optional metric value
    •   optional unit of metric
    """
```


usage:

```py
from pipa.parser.perf_stat import parse_perf_stat_file
perf_stat_df  = parse_perf_stat_file(stat_output_path)
```



### perf record

```py
def parse_perf_script_file(parsed_script_path):
    """
    Parses a perf script file and returns the data as a pandas DataFrame.

    Args:
        parsed_script_path (str): The path to the perf script file.

    Returns:
        pandas.DataFrame: The parsed data as a DataFrame.
    """
```

usage:

```py
from pipa.parser.perf_stat import parse_perf_stat_file
perf_stat_df  = parse_perf_stat_file(stat_output_path)
```

## run

The following script run `perf stat` and `sar` at the same time. And then run `perf record` to profile.

To gengerate the data which above functions could parse, you only need to ensure the `perf script` & `perf stat` & `sar` output saved successfully.

```sh
#!/bin/bash

init() {
    # Create a directory to store the output of the script
    if [ ! -d "./data/dump" ]; then
        mkdir -p ./data/dump
    fi
}

# Function to collect performance records using 'perf' command
# Example:
# collect_perf_record "perf bench futex hash" 97 "./data/dump/workload_$(date +%s).log" "instructions,ref-cycles,cpu-cycles,branch-instructions,branch-misses"
collect_perf_record() {
    workload_cmd="${1:-perf bench futex hash}"
    frequency="${2:-97}"
    script_path="${3:-}"
    events="${4:-instructions,ref-cycles,cpu-cycles,branch-instructions,branch-misses}"

    now=$(date +%s)
    if [ -z "$script_path" ]; then
        script_path="./data/dump/workload_${now}.log"
    fi

    # Construct the command to record the CPU events
    perf record -e "$events" -a -F "$frequency" "$workload_cmd" >"$script_path"

    # Generate a performance report
    report_path="./data/dump/perf_${now}.report"
    perf report --header >"$report_path"

    # Generate output of the perf script
    script_path="./data/dump/perf_${now}.script"
    perf script --header >"$script_path"

    mv "perf.data" "./data/dump/perf_${now}.data"

    echo "$report_path $script_path"
}

# Function to collect performance statistics using 'perf stat' command
# Example:
# collect_perf_stat "perf bench futex hash" 997 "./data/dump/perf_stat_$(date +%s).csv" "instructions,ref-cycles,cpu-cycles,branch-instructions,branch-misses" "0-19"
collect_perf_stat() {
    workload_cmd="${1:-perf bench futex hash}"
    sample_rate="${2:-997}"
    perf_stat_output_path="${3:-}"
    events="${4:-instructions,ref-cycles,cpu-cycles,branch-instructions,branch-misses}"
    core_range="${5:-0-19}"

    now=$(date +%s)
    perf_stat_output_path="${perf_stat_output_path:-./data/dump/perf_stat_${now}.csv}"

    perf stat -e $events -C $core_range -A -x , -I $sample_rate -o $perf_stat_output_path $workload_cmd

    echo "$perf_stat_output_path"
}

# Function to collect performance statistics using perf stat and sar commands
# Example:
# collect_perf_stat_with_sar "perf bench futex hash" 1000 "./data/dump/perf_stat_$(date +%s).csv" "./data/dump/sar_output_$(date +%s).dat"
collect_perf_stat_with_sar() {
    workload_cmd="${1:-perf bench futex hash}"
    sample_rate="${2:-1000}"
    perf_stat_output_path="${3:-}"
    sar_output_path="${4:-}"
    events="${5:-instructions,ref-cycles,cpu-cycles,branch-instructions,branch-misses}"
    core_range="${6:-0-19}"

    sar_output_path="${sar_output_path:-./data/dump/sar_output_$(date +%s).dat}"
    sar -o "$sar_output_path" 1 >/dev/null 2>&1 &

    perf_stat_output_path=$(collect_perf_stat "$workload_cmd" "$sample_rate" "$perf_stat_output_path" "$events" "$core_range")

    killall sar

    echo "sar_output_path: $sar_output_path"
    echo "perf_stat_output_path: $perf_stat_output_path"
}

# Main script
if [ "$0" = "$BASH_SOURCE" ]; then
    init
    collect_perf_stat_with_sar
    collect_perf_record
fi

```