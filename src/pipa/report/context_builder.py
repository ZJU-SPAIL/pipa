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
        "avg_iowait": 0.0,
        "avg_nvcswch_s": 0.0,
        "cpu_util_std_dev": 0.0,
        "cpu_max_util": 0.0,
        "cpu_min_util": 0.0,
    }

    if static_info and (cpu_info := static_info.get("cpu_info")):
        context["num_cpu"] = cpu_info.get("CPUs_Count", 1)

    df_cpu = df_dict.get("sar_cpu")
    if df_cpu is not None and not df_cpu.empty:
        df_per_core = df_cpu[df_cpu["CPU"] != "all"].copy()
        if not df_per_core.empty:
            if "%user" in df_per_core.columns and "%system" in df_per_core.columns:
                df_per_core["%total"] = df_per_core["%user"] + df_per_core["%system"]
            else:
                df_per_core["%total"] = 0.0

            core_avg_utils = df_per_core.groupby("CPU")["%total"].mean()

            context["cpu_util_std_dev"] = core_avg_utils.std()
            context["cpu_max_util"] = core_avg_utils.max()
            context["cpu_min_util"] = core_avg_utils.min()

        df_cpu_all = df_cpu[df_cpu["CPU"] == "all"]
        if not df_cpu_all.empty:
            context["total_cpu"] = (
                df_cpu_all.get("%user", pd.Series(0)).mean() + df_cpu_all.get("%system", pd.Series(0)).mean()
            )
            context["avg_irq_percent"] = df_cpu_all.get("%irq", pd.Series(0)).mean()
            context["avg_softirq_percent"] = df_cpu_all.get("%soft", pd.Series(0)).mean()
            context["avg_iowait"] = df_cpu_all.get("%iowait", pd.Series(0)).mean()

    df_io = df_dict.get("sar_io")
    if df_io is not None and not df_io.empty:
        context["total_tps"] = df_io.get("tps", pd.Series(0)).sum()
        context["avg_await"] = df_io.get("await", pd.Series(0)).mean()
        context["avg_util"] = df_io.get("%util", pd.Series(0)).mean()
        context["avg_avgrq_sz"] = df_io.get("avgrq-sz", pd.Series(0)).mean()
        context["avg_avgqu_sz"] = df_io.get("avgqu-sz", pd.Series(0)).mean()
        context["avg_bread_s"] = df_io.get("bread/s", pd.Series(0)).mean()
        context["avg_bwrtn_s"] = df_io.get("bwrtn/s", pd.Series(0)).mean()

    df_paging = df_dict.get("sar_paging")
    if df_paging is not None and not df_paging.empty:
        context["avg_swaps"] = (
            df_paging.get("pgpgin/s", pd.Series(0)).mean() + df_paging.get("pgpgout/s", pd.Series(0)).mean()
        )
        context["avg_majflt_s"] = df_paging.get("majflt/s", pd.Series(0)).mean()

    df_cswch = df_dict.get("sar_cswch")
    if df_cswch is not None and not df_cswch.empty:
        context["avg_cswch"] = df_cswch.get("proc/s", pd.Series(0)).mean()
        context["avg_nvcswch_s"] = df_cswch.get("nvcswch/s", pd.Series(0)).mean()

    df_memory = df_dict.get("sar_memory")
    if df_memory is not None and not df_memory.empty:
        context["avg_memused_percent"] = df_memory.get("%memused", pd.Series(0)).mean()
        context["avg_commit_percent"] = df_memory.get("%commit", pd.Series(0)).mean()
        context["avg_kbcached"] = df_memory.get("kbcached", pd.Series(0)).mean()
        context["avg_kbactive"] = df_memory.get("kbactive", pd.Series(0)).mean()

    df_load = df_dict.get("sar_load")
    if df_load is not None and not df_load.empty:
        context["avg_load1"] = df_load.get("ldavg-1", pd.Series(0)).mean()

    df_network = df_dict.get("sar_network")
    if df_network is not None and not df_network.empty:
        context["avg_rxkB_s"] = df_network.get("rxkB/s", pd.Series(0)).mean()
        context["avg_txkB_s"] = df_network.get("txkB/s", pd.Series(0)).mean()
        context["avg_ifutil"] = df_network.get("%ifutil", pd.Series(0)).mean()

    if (df_perf_raw := df_dict.get("perf_raw")) is not None and not df_perf_raw.empty:
        df_perf_all = df_perf_raw[df_perf_raw["cpu"] == "all"].copy()
        if not df_perf_all.empty:

            def get_event_sum(event_names: list) -> float:
                series = df_perf_all[df_perf_all["event_name"].isin(event_names)]["value"]
                return series.sum() if not series.empty else 0.0

            instructions = get_event_sum(["instructions", "inst_retired.any"])
            cycles = get_event_sum(["cycles", "cpu-cycles"])
            slots = cycles * 4

            if cycles > 0:
                context["ipc"] = instructions / cycles

            if slots > 0:
                context["tma_retiring"] = (instructions / slots) * 100

                frontend_latency_cycles = get_event_sum(["stalled-cycles-frontend", "frontend_latency_cycles"])
                context["tma_frontend_bound"] = (frontend_latency_cycles / slots) * 100

                branch_mispredicts_retired = get_event_sum(["branch-misses", "branch-mispredicts-retired"])
                bad_spec_cycles = branch_mispredicts_retired * 20
                context["tma_bad_speculation"] = (bad_spec_cycles / slots) * 100

                backend_bound = 100 - (
                    context["tma_retiring"] + context["tma_frontend_bound"] + context["tma_bad_speculation"]
                )
                context["tma_backend_bound"] = max(0, backend_bound)

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

            cswch_series = df_perf_all[df_perf_all["event_name"] == "context-switches"]["value"]
            if not cswch_series.empty:
                context["avg_cswch"] = cswch_series.mean()

    return context
