"""Parser utilities and registry."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

import plotly.graph_objects as go

from .perf_stat import parse_perf_stat_timeseries
from .sar_parsers import generic_sar_parse, parse_sar_cpu


def make_single_plot(
    scatters: List[go.Scatter],
    title: str,
    xaxis_title: str,
    yaxis_title: str,
    show: bool = True,
    write_to_html: Optional[str] = None,
) -> go.Figure:
    """Render a Plotly figure from a list of scatter traces."""

    figure = go.Figure()
    for scatter in scatters:
        figure.add_trace(scatter)
    figure.update_layout(
        title=title,
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        hovermode="closest",
    )
    if show:
        figure.show()
    if write_to_html:
        figure.write_html(write_to_html)
    return figure


PARSER_REGISTRY: Dict[str, Callable] = {
    "perf_stat": parse_perf_stat_timeseries,
    "sar_cpu": parse_sar_cpu,
    "sar_io": generic_sar_parse,
    "sar_disk": generic_sar_parse,
    "sar_load": generic_sar_parse,
    "sar_memory": generic_sar_parse,
    "sar_network": generic_sar_parse,
    "sar_paging": generic_sar_parse,
}

__all__ = ["make_single_plot", "PARSER_REGISTRY"]
