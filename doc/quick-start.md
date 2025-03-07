# Quick Start

This document takes you through the basics of using pipa by measuring the performance of the perf bench as an example.

## Installation

Use the following command to install the package:

```shell
pip install pypipa
```

## Data Collection

First of all, use command `pipa generate`

```sh
❯ pipa generate
? Please select the way of workload you want to run. Build a script that collects performance data and start the workloa
d by perf.
? Where do you want to store your data? (Default: ./)
 ./data
? What's the frequency of perf-record? (Default: 999)
 999
? What's the event of perf-record? (Default: {cycles,instructions}:S)
 {cycles,instructions}:S
? Whether to use perf-annotate?
 No
? Do you want to use perf-stat or emon?
 perf-stat
? What's count deltas of perf-stat? (Default: 1000 milliseconds)
 1000
? What's the event of perf-stat?
 cycles,instructions,branch-misses,L1-dcache-load-misses,L1-icache-load-misses
? Whether to use taskset?
 Yes
? Which cores do you want to use? (Default: 0-47)
 0-47
? What's the command of workload?
 perf bench futex hash
Shell script generated successfully.
Please check the script in ./data/pipa-run.sh
Note that you may need to modify the script to meet your requirements. The core list is generated according to the
machine which runs this script now. pipa-run.sh is more suitable for reproducible workloads such as benchmark.
```

In this example, we use the `perf bench futex hash` as the observed workload, which is a micro benchmark that comes with perf. As long as perf is installed successfully, you don't need to install any dependencies to run this example.

If all goes well, you will get the following script, in the `data/pipa-run.sh`.

```sh
#!/bin/bash
# The script generated by PIPA-TREE is used to collect performance data.
# Please check whether it meets expectations before running.
# ZJU SPAIL(https://github.com/ZJU-SPAIL) reserves all rights.
# Generated at 2024-09-16T22:40:11.582583

# Check if sar and perf are available
if ! command -v sar &> /dev/null; then
echo "sar command not found. Please install sar."
exit 1
fi

if ! command -v perf &> /dev/null; then
echo "perf command not found. Please install perf."
exit 1
fi

WORKSPACE=./data
mkdir -p $WORKSPACE

ps -aux -ef --forest --sort=-%cpu > $WORKSPACE/ps.txt
perf record -e '{cycles,instructions}:S' -g -a -F 999 -o $WORKSPACE/perf.data /usr/bin/taskset -c 0-47 perf bench futex hash
perf script -i $WORKSPACE/perf.data -I --header > $WORKSPACE/perf.script
perf report -i $WORKSPACE/perf.data -I --header > $WORKSPACE/perf.report

sar -o $WORKSPACE/sar.dat 1 >/dev/null 2>&1 &
sar_pid=$!
perf stat -e cycles,instructions,branch-misses,L1-dcache-load-misses,L1-icache-load-misses -C 0-47 -A -x , -I 1000 -o $WORKSPACE/perf-stat.csv /usr/bin/taskset -c 0-47 perf bench futex hash
kill -9 $sar_pid
LC_ALL='C' sar -A -f $WORKSPACE/sar.dat >$WORKSPACE/sar.txt

DST="./data/config"
mkdir -p ./data/config
if [[ $(id -u) -eq 0 ]]; then
    # User is root, run dmidecode directly
    dmidecode >/$DST/dmidecode.txt
else
    echo "You need to be root to run dmidecode, skipping..."
fi

if command -v lspci &>/dev/null; then
    lspci >"$DST/pci_devices.txt"
    echo "PCI devices exported to $DST/pci_devices.txt"
fi

if command -v lsusb &>/dev/null; then
    lsusb >"$DST/usb_devices.txt"
    echo "USB devices exported to $DST/usb_devices.txt"
fi

if command -v lsblk &>/dev/null; then
    lsblk >"$DST/block_devices.txt"
    echo "Block devices exported to $DST/block_devices.txt"
fi

if command -v lshw &>/dev/null; then
    lshw >"$DST/hardware.txt"
    echo "Hardware information exported to $DST/hardware.txt"
fi

if command -v lscpu &>/dev/null; then
    lscpu >"$DST/cpu.txt"
    echo "CPU information exported to $DST/cpu.txt"
    lscpu -a --extended >"$DST/cpu-extended.txt"
    echo "Extended CPU information exported to $DST/cpu-extended.txt"
fi

if command -v lsmod &>/dev/null; then
    lsmod >"$DST/modules.txt"
    echo "Kernel modules exported to $DST/modules.txt"
fi

if command -v lsinitrd &>/dev/null; then
    lsinitrd >"$DST/initrd.txt"
    echo "Initrd information exported to $DST/initrd.txt"
fi

if command -v ip &>/dev/null; then
    ip addr >"$DST/ip.txt"
    echo "IP information exported to $DST/ip.txt"
fi

df -h >"$DST/disk_usage.txt"
echo "Disk usage exported to $DST/disk_usage.txt"

cp /proc/meminfo "$DST/meminfo.txt"
echo "Memory information exported to $DST/meminfo.txt"

cp /proc/cpuinfo "$DST/cpuinfo.txt"
echo "CPU information exported to $DST/cpuinfo.txt"

perf list > "$DST/perf-list.txt"
echo "Perf list exported to $DST/perf-list.txt"

ulimit -a > "$DST/ulimit.txt"
echo "Ulimit information exported to $DST/ulimit.txt"

echo "Configuration exported to $DST"


echo 'Performance data collected successfully.'
```


This script will run the workload twice, using `perf record` and` perf stat` + `sar` to make observations and save the corresponding data. In addition, before running, the process data will be checked to determine the noise level, and after running, the system configuration file will be exported.

After the running script is built, you can run it and redirect the results to a file.

```shell
bash ./data/pipa-run.sh > ./data/pipa-run.log
```

## Data Loading & Visualization

Before running the following data loading and visualization steps, we recommend that you configure your Python and Jupyter notebook environments.

```py
from pipa.service.pipashu import PIPAShuData

pipashu = PIPAShuData(
    perf_stat_path="./data/perf-stat.csv",
    sar_path="./data/sar.txt",
    perf_record_path="./data/perf.script",
)
```

We can find the following output information in pipa-run.log.

```bash
# Running 'futex/hash' benchmark:
Run summary [PID 206133]: 48 threads, each operating on 1024 [private] futexes for 10 secs.

[thread  0] futexes: 0x55699956b260 ... 0x55699956c25c [ 2659737 ops/sec ]
[thread  1] futexes: 0x55699956d100 ... 0x55699956e0fc [ 2674176 ops/sec ]
[thread  2] futexes: 0x55699956e110 ... 0x55699956f10c [ 2684006 ops/sec ]
[thread  3] futexes: 0x55699956f120 ... 0x55699957011c [ 2683187 ops/sec ]
[thread  4] futexes: 0x556999570130 ... 0x55699957112c [ 2661683 ops/sec ]
[thread  5] futexes: 0x556999571140 ... 0x55699957213c [ 2674688 ops/sec ]
[thread  6] futexes: 0x556999572150 ... 0x55699957314c [ 2691174 ops/sec ]
[thread  7] futexes: 0x556999573310 ... 0x55699957430c [ 2678988 ops/sec ]
[thread  8] futexes: 0x5569995744d0 ... 0x5569995754cc [ 2659328 ops/sec ]
[thread  9] futexes: 0x556999575690 ... 0x55699957668c [ 2685644 ops/sec ]
[thread 10] futexes: 0x556999576850 ... 0x55699957784c [ 2702028 ops/sec ]
[thread 11] futexes: 0x556999577a10 ... 0x556999578a0c [ 2661785 ops/sec ]
[thread 12] futexes: 0x556999578bd0 ... 0x556999579bcc [ 2669977 ops/sec ]
[thread 13] futexes: 0x556999579d90 ... 0x55699957ad8c [ 2700800 ops/sec ]
[thread 14] futexes: 0x55699957af50 ... 0x55699957bf4c [ 2709708 ops/sec ]
[thread 15] futexes: 0x55699957c110 ... 0x55699957d10c [ 2667212 ops/sec ]
[thread 16] futexes: 0x55699957d2d0 ... 0x55699957e2cc [ 2686566 ops/sec ]
[thread 17] futexes: 0x55699957e490 ... 0x55699957f48c [ 2693222 ops/sec ]
[thread 18] futexes: 0x55699957f650 ... 0x55699958064c [ 2685030 ops/sec ]
[thread 19] futexes: 0x556999580810 ... 0x55699958180c [ 2680729 ops/sec ]
[thread 20] futexes: 0x5569995819d0 ... 0x5569995829cc [ 2686361 ops/sec ]
[thread 21] futexes: 0x556999582b90 ... 0x556999583b8c [ 2679603 ops/sec ]
[thread 22] futexes: 0x556999583d50 ... 0x556999584d4c [ 2665984 ops/sec ]
[thread 23] futexes: 0x556999584f10 ... 0x556999585f0c [ 2695475 ops/sec ]
[thread 24] futexes: 0x5569995860d0 ... 0x5569995870cc [ 2686873 ops/sec ]
[thread 25] futexes: 0x556999587290 ... 0x55699958828c [ 2693734 ops/sec ]
[thread 26] futexes: 0x556999588450 ... 0x55699958944c [ 2679398 ops/sec ]
[thread 27] futexes: 0x556999589610 ... 0x55699958a60c [ 2690150 ops/sec ]
[thread 28] futexes: 0x55699958a7d0 ... 0x55699958b7cc [ 2696396 ops/sec ]
[thread 29] futexes: 0x55699958b990 ... 0x55699958c98c [ 2689433 ops/sec ]
[thread 30] futexes: 0x55699958cb50 ... 0x55699958db4c [ 2707456 ops/sec ]
[thread 31] futexes: 0x55699958dd10 ... 0x55699958ed0c [ 2698240 ops/sec ]
[thread 32] futexes: 0x55699958eed0 ... 0x55699958fecc [ 2702745 ops/sec ]
[thread 33] futexes: 0x556999590090 ... 0x55699959108c [ 2681241 ops/sec ]
[thread 34] futexes: 0x556999591250 ... 0x55699959224c [ 2685235 ops/sec ]
[thread 35] futexes: 0x556999592410 ... 0x55699959340c [ 2688307 ops/sec ]
[thread 36] futexes: 0x5569995935d0 ... 0x5569995945cc [ 2679193 ops/sec ]
[thread 37] futexes: 0x556999594790 ... 0x55699959578c [ 2671308 ops/sec ]
[thread 38] futexes: 0x556999595950 ... 0x55699959694c [ 2681958 ops/sec ]
[thread 39] futexes: 0x556999596b10 ... 0x556999597b0c [ 2656972 ops/sec ]
[thread 40] futexes: 0x556999597cd0 ... 0x556999598ccc [ 2614476 ops/sec ]
[thread 41] futexes: 0x556999598e90 ... 0x556999599e8c [ 2625331 ops/sec ]
[thread 42] futexes: 0x55699959a050 ... 0x55699959b04c [ 2664038 ops/sec ]
[thread 43] futexes: 0x55699959b210 ... 0x55699959c20c [ 2651852 ops/sec ]
[thread 44] futexes: 0x55699959c3d0 ... 0x55699959d3cc [ 2637824 ops/sec ]
[thread 45] futexes: 0x55699959d590 ... 0x55699959e58c [ 2640384 ops/sec ]
[thread 46] futexes: 0x55699959e750 ... 0x55699959f74c [ 2667724 ops/sec ]
[thread 47] futexes: 0x55699959f910 ... 0x5569995a090c [ 2651648 ops/sec ]

Averaged 2676646 operations/sec (+- 0.09%), total secs = 10
```

After summing the above throughput and multiplying the time (10 seconds), we can calculate the total number of transactions, which is 1284790070.


After that, we can use pipa's data based on perf-stat and sar to calculate some general metrics, covering CPU, memory, and disk.

```py
pipashu.get_metrics(num_transcations = 1284790070, threads = list(range(48)))
```

It is worth noting that by default, if no disk is specified, the disk with the highest utilization will be selected. The best practice is for users to identify which disk they are using before running the experiment and pass it here as a parameter.

```py
def get_metrics(
    num_transcations: int,
    threads: list,
    run_time: int = None,
    dev: str | None = None,
    freq_MHz: int = None
):
    pass
```

## Upload
PIPA provides two ways to upload your performance data with detailed information. One is to upload in command line interation, and the other is to upload with YAML.

### Upload in cmd interaction manner
Use the following command line to upload data in a cmd interaction manner:
```shell
pipa upload
```
Then 
```bash
? What's the name of workload? Kafka
? What's the number of transaction? 10000000
? Where's the data collected by PIPAShu? data
? What are the threads used in the workload? Split by , 0,1,2,3
? What's the used disk device name? dm-2
? What's the hardware configuration (sockets*cores*SMT)? 1*1*1
? What's the software configuration? JDK1.8
? What's the platform? IceLake 8383C
? Any comments?
? What's the PIPAD server address?
? What's the PIPAD server port?
```

### Upload with YAML
Use the following command line to upload data with YAML:
```shell
pipa upload <config_file>
```
PIPA provides a template configuration file [config-upload.yaml](https://github.com/ZJU_SPAIL/pipa/blob/main/asset/config-upload.yaml).
```yaml
# PIPA-Shu Upload Configuration
# Use pipa upload to upload the data to PIPAD server based on this configuration.
# Command Example: pipa upload --config_path=./data/config-upload.yaml
workload: rocksdb
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
cpu_frequency_mhz: 2600
# The CPU frequency in MHz.
# Only needed when the platform is Huawei.

comment: "This is a template for the upload configuration."
# Any comments.
pipad_addr: 10.82.77.113
# The PIPAD server address.
pipad_port: 50051
# The PIPAD server port.

```

Data location is the directory of your PIPASHU data. It should at least include:
```bash
data/
├── perf-stat.csv
├── perf.script
└── sar.txt
```

So far, pipa's grafana panel has only been calculated based on data from perf-stat and sar. If perf.script is particularly large, you might consider not importing a perf.script file to speed things up. You just need to replace the `data_location` field with the `perf_stat_path`, `sar_path` field.

BTW, cores list is the cores you want to focus on. To get the list quickly, you can use python list.

```shell
$ python
Python 3.11.5 (main, Sep 11 2023, 13:54:46) [GCC 11.2.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> list(range(32,64))
[32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63]
```


## Dump

Before formally uploading PIPASHU data, you can use PIPA dump to dump overview data to a file for double check.

```shell
pipa dump -o <output_file> -c <config_file> -v
```
`-c <config_file>`: PIPA provides a template config file [config-upload.yaml](https://github.com/ZJU_SPAIL/pipa/blob/main/asset/config-upload.yaml).If this parameter is missed, you can dump data in a cmd interaction manner. 

`-v`: If this parameter is used, output file will be printed to the screen.
