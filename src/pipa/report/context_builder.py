from typing import Any, Dict

import pandas as pd


def build_full_context(df_dict: Dict[str, pd.DataFrame], static_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Builds a comprehensive context dictionary containing all derived metrics
    needed by the rules engine, plotter, and HTML template.
    """
    context: Dict[str, Any] = {
        "num_cpu": 1,
        "total_cpu": 0.0,
        "avg_cswch": 0.0,
        "total_tps": 0.0,
        "avg_swaps": 0.0,
        "avg_load1": 0.0,
        "ipc": 0.0,
        "branch_miss_rate": 0.0,
        "l3_cache_miss_rate": 0.0,
    }

    if static_info and (cpu_info := static_info.get("cpu_info")):
        context["num_cpu"] = cpu_info.get("CPUs_Count", 1)

    df_cpu = df_dict.get("sar_cpu")
    if df_cpu is not None and not df_cpu.empty:
        df_cpu_all = df_cpu[df_cpu["CPU"] == "all"]
        if not df_cpu_all.empty:
            context["total_cpu"] = (
                df_cpu_all.get("%user", pd.Series(0)).mean() + df_cpu_all.get("%system", pd.Series(0)).mean()
            )

    df_cswch = df_dict.get("proc_cswch")
    if df_cswch is not None and not df_cswch.empty:
        context["avg_cswch"] = df_cswch.get("cswch_per_s", pd.Series(0)).mean()

    df_io = df_dict.get("sar_io")
    if df_io is not None and not df_io.empty:
        context["total_tps"] = df_io.get("tps", pd.Series(0)).sum()

    df_paging = df_dict.get("sar_paging")
    if df_paging is not None and not df_paging.empty:
        context["avg_swaps"] = (
            df_paging.get("pgpgin/s", pd.Series(0)).mean() + df_paging.get("pgpgout/s", pd.Series(0)).mean()
        )

    df_load = df_dict.get("sar_load")
    if df_load is not None and not df_load.empty:
        context["avg_load1"] = df_load.get("ldavg-1", pd.Series(0)).mean()

    if (df_perf_raw := df_dict.get("perf_raw")) is not None and not df_perf_raw.empty:
        df_perf_all = df_perf_raw[df_perf_raw["cpu"] == "all"].copy()
        if not df_perf_all.empty:
            instructions = df_perf_all[df_perf_all["event_name"].isin(["instructions", "inst_retired.any"])][
                "value"
            ].sum()
            cycles = df_perf_all[df_perf_all["event_name"].isin(["cycles", "cpu-cycles"])]["value"].sum()
            if cycles > 0:
                context["ipc"] = instructions / cycles

            branch_instructions = df_perf_all[df_perf_all["event_name"] == "branch-instructions"]["value"].sum()
            branch_misses = df_perf_all[df_perf_all["event_name"] == "branch-misses"]["value"].sum()
            if branch_instructions > 0:
                context["branch_miss_rate"] = (branch_misses / branch_instructions) * 100

            llc_loads = df_perf_all[df_perf_all["event_name"].isin(["LLC-loads", "ll_cache_rd"])]["value"].sum()
            llc_misses = df_perf_all[df_perf_all["event_name"].isin(["LLC-load-misses", "ll_cache_miss_rd"])][
                "value"
            ].sum()
            if llc_loads > 0:
                context["l3_cache_miss_rate"] = (llc_misses / llc_loads) * 100

    return context
