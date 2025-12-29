"""Reporting utilities for HTML and visualization generation."""

from .cluster_analyzer import analyze_cpu_clusters
from .context_builder import build_full_context
from .hotspots import extract_hotspots
from .html_generator import generate_html_report
from .plotter import (
    plot_cpu_clusters,
    plot_disk_sunburst,
    plot_per_disk_pies,
    plot_sar_cpu,
    plot_timeseries_generic,
)

__all__ = [
    "analyze_cpu_clusters",
    "build_full_context",
    "extract_hotspots",
    "generate_html_report",
    "plot_cpu_clusters",
    "plot_disk_sunburst",
    "plot_per_disk_pies",
    "plot_sar_cpu",
    "plot_timeseries_generic",
]
