from __future__ import annotations

from ._base_sar_parser import generic_sar_parse
from .sar_cpu_parser import parse as parse_sar_cpu

SAR_PARSER_REGISTRY = {
    "sar_cpu": parse_sar_cpu,
    "sar_io": generic_sar_parse,
    "sar_disk": generic_sar_parse,
    "sar_load": generic_sar_parse,
    "sar_memory": generic_sar_parse,
    "sar_network": generic_sar_parse,
    "sar_paging": generic_sar_parse,
}

__all__ = ["SAR_PARSER_REGISTRY", "generic_sar_parse", "parse_sar_cpu"]
