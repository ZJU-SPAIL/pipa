def build_perf_stat_cmd(
    events_stat: str,
    core_list: str,
    count_delta_stat: int,
    command: str,
    workspace: str,
) -> str:

    return (
        f"perf stat -e {events_stat} -C {core_list} "
        f"-A -x , -I {count_delta_stat} -o {workspace}/perf-stat.csv {command}\n"
    )
