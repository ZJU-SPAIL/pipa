from pipa.parser.perf_script import parse_perf_script_file
from pipa.parser.perf_stat import parse_perf_stat_file
from pipa.parser.sar import parse_sar_bin
from pipa.service.collect import collect_perf_record, collect_perf_stat_with_sar


def run_and_collect_all(workload_cmd: str):
    perf_stat_dump_path, sar_dump_path = collect_perf_stat_with_sar(
        workload_cmd=workload_cmd
    )
    sar_df_list = parse_sar_bin(sar_dump_path)
    perf_stat_df = parse_perf_stat_file(perf_stat_dump_path)

    report_dump_path, script_dump_path = collect_perf_record(workload_cmd=workload_cmd)
    perf_script_df = parse_perf_script_file(script_dump_path)
    return sar_df_list, perf_stat_df, perf_script_df


if __name__ == "__main__":
    sar_df_list, perf_stat_df, perf_script_df = run_and_collect_all(
        "perf bench futex hash"
    )
    print(sar_df_list)
    print(perf_stat_df)
    print(perf_script_df)
