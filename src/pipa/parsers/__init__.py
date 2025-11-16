# --- 导入我们仅有的两个逻辑上独立的解析器 ---
from ._base_sar_parser import generic_sar_parse
from .perf_stat_timeseries_parser import parse as parse_perf_stat
from .sar_cpu_parser import parse as parse_sar_cpu

# --- The Parser Registry ---
# 核心: 多个键直接引用同一个 `generic_sar_parse` 函数对象。
# 零重复，零 boilerplate。
PARSER_REGISTRY = {
    "perf_stat": parse_perf_stat,
    "sar_cpu": parse_sar_cpu,
    "sar_io": generic_sar_parse,
    "sar_load": generic_sar_parse,
    "sar_memory": generic_sar_parse,
    "sar_network": generic_sar_parse,
    "sar_paging": generic_sar_parse,
}

__all__ = ["PARSER_REGISTRY"]
