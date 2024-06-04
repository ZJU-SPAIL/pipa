# PIPA-tree

perf-record

The perf tool can be used to collect profiles on `per-thread`, `per-process` and `per-cpu` basis.

support P-core only


## cycles

> By default, perf record uses the cycles event as the sampling event. This is a generic hardware event that is mapped to a hardware-specific PMU event by the kernel. For Intel, it is mapped to UNHALTED_CORE_CYCLES. This event does not maintain a constant correlation to time in the presence of CPU frequency scaling. Intel provides another event, called UNHALTED_REFERENCE_CYCLES but this event is NOT currently available with perf_events.  
> On AMD systems, the event is mapped to CPU_CLK_UNHALTED and this event is also subject to frequency scaling. On any Intel or AMD processor, the cycle event does not count when the processor is idle, i.e., when it calls mwait().

## hardware events

```
branch-instructions
branch-misses
cache-misses    
cache-references
bus-cycles   
instructions
cycles
ref-cycles
```


```
L1-dcache-loads OR cpu_core/L1-dcache-loads/
L1-dcache-load-misses OR cpu_core/L1-dcache-load-misses/
L1-dcache-stores OR cpu_core/L1-dcache-stores/
L1-icache-load-misses OR cpu_core/L1-icache-load-misses/
LLC-loads OR cpu_core/LLC-loads/
LLC-load-misses OR cpu_core/LLC-load-misses/
LLC-stores OR cpu_core/LLC-stores/
LLC-store-misses OR cpu_core/LLC-store-misses/
dTLB-loads OR cpu_core/dTLB-loads/
dTLB-load-misses OR cpu_core/dTLB-load-misses/
dTLB-stores OR cpu_core/dTLB-stores/
dTLB-store-misses OR cpu_core/dTLB-store-misses/
iTLB-load-misses OR cpu_core/iTLB-load-misses/
branch-loads OR cpu_core/branch-loads/
branch-load-misses OR cpu_core/branch-load-misses/
node-loads OR cpu_core/node-loads/
node-load-misses OR cpu_core/node-load-misses/
```

## todo

1. 采集数据 导入csv
   1. `cpu_clk_unhalted.ref_tsc`/`TSC`
2. 支持black grey
3. 支持程序不同的启动模式
   1. 从 perf 启动 
   2. 监听全局
   3. 指定 core
4. 单元测试


```sh
# skylake
perf stat -e uops_issued.any,uops_executed,uops_retired.all a.exe
# newer
perf stat -e uops_issued.any,uops_executed,uops_retired.retire_slots a.exe


perf report > perf.report

# There are many different ways samples can be presented, i.e., sorted. To sort by shared objects, i.e., dsos:
perf report --sort=dso


perf script --header -F comm,pid,tid,cpu,time,event,ip,sym,dso > perf.script # ,trace
```

```sh
perf stat

perf stat -a -A -e {instructions,ref-cycles,cpu-cycles,branch-instructions,branch-misses} -x, -o stat.csv perf bench futex hash
# Workload failed: No such file or directory

perf stat -C 0-11 -A -I 1000 -e \{cpu_core/cycles/,cpu_core/instructions/,cpu_core/L1-dcache-loads/,cpu_core/L1-dcache-load-misses/,cpu_core/LLC-loads/,cpu_core/LLC-load-misses/} -x, -o  stat.csv perf bench futex hash
```


`perf -g`  trace

```sh
# 栈指针 CPU栈踪迹
perf record -e ref-cycles -F 9997 -g ./out/O0g.out

# last branch record LBR CPU栈踪迹
perf record -e ref-cycles -F 9997 -g --call-graph lbr ./out/O0g.out

# dwarf debuginfo CPU栈踪迹
perf record -e ref-cycles -F 9997 -g --call-graph dwarf ./out/O0g.out
```


```sh
perf_events="cycles,instructions,ref-cycles,branches,branch-misses,L1-icache-loads,L1-icache-load-misses,LLC-load-misses"
perf_command="perf stat -C 0-19 -A -I 1000 -e ${perf_events} -x, -o ./perf.data
```

`perf annotate` can generate sourcecode level information if the application is compiled with -ggdb. The following snippet shows the much more informative output for the same execution of noploop when compiled with this debugging information.