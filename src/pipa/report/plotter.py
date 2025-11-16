from typing import Dict, Tuple

import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure


def plot_sar_cpu(df: pd.DataFrame) -> Figure:
    """
    Generates an interactive Plotly figure for sar_cpu data.
    """
    if "%user" in df.columns and "%system" in df.columns:
        df["%total"] = df["%user"] + df["%system"]

    metrics_to_plot = [m for m in ["%user", "%system", "%iowait", "%idle", "%total"] if m in df.columns]

    melted_df = df.melt(
        id_vars=["timestamp", "CPU"],
        value_vars=metrics_to_plot,
        var_name="metric",
        value_name="utilization",
    )

    fig = px.line(
        melted_df,
        x="timestamp",
        y="utilization",
        color="CPU",
        line_dash="metric",
        title="Sar CPU Metrics (Per-Core & Overall)",
        labels={"utilization": "CPU Utilization (%)"},
    )

    fig.update_layout(
        height=600,
        showlegend=True,
        legend=dict(
            title="Metrics",
            orientation="v",
            yanchor="top",
            y=1.0,
            xanchor="left",
            x=1.01,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="rgba(0,0,0,0.2)",
            borderwidth=1,
        ),
        margin=dict(r=200),
    )
    return fig


def plot_timeseries_generic(df: pd.DataFrame, name: str) -> Tuple[Dict[str, Figure], Dict[str, Dict]]:
    """
    Generates interactive Plotly figures for any generic time-series DataFrame.
    It intelligently splits metrics into 'percent' and 'absolute' plots if needed.
    Returns a tuple containing:
    1. A dictionary of generated plot figures {plot_name: Figure}.
    2. A dictionary of filter context for the template {plot_name_filters: {...}}.
    """
    generated_plots: Dict[str, Figure] = {}
    generated_filters: Dict[str, Dict] = {}

    percent_cols = [c for c in df.columns if "%" in c and df[c].dtype.kind in "if"]
    absolute_cols = [
        c
        for c in df.columns
        if df[c].dtype.kind in "if" and c not in percent_cols and c not in ["interval", "hostname"]
    ]
    id_col = next((col for col in ["IFACE", "DEV", "cpu"] if col in df.columns), None)

    metric_groups = {}
    if percent_cols:
        metric_groups["percent"] = percent_cols
    if absolute_cols:
        metric_groups["absolute"] = absolute_cols

    for metric_type, cols_to_plot in metric_groups.items():
        if not cols_to_plot:
            continue

        plot_name = f"{name}_{metric_type}" if len(metric_groups) > 1 else name
        melted_df = df.melt(
            id_vars=["timestamp"] + ([id_col] if id_col else []),
            value_vars=cols_to_plot,
            var_name="metric",
            value_name="value",
        )
        if melted_df.empty:
            continue

        chart_title = f"{name.replace('_', ' ').title()} Metrics"
        y_axis_title = "Value"
        if name == "sar_load":
            chart_title = "System Load & Run Queue Length"
        if metric_type == "percent":
            y_axis_title = "Percentage (%)"
            if len(metric_groups) > 1:
                chart_title += " (Percentages)"
        elif len(metric_groups) > 1:
            chart_title += " (Absolute Values)"

        fig = px.line(
            melted_df,
            x="timestamp",
            y="value",
            color="metric",
            line_dash=id_col,
            title=chart_title,
            labels={"value": y_axis_title},
        )
        fig.update_layout(
            height=500,
            showlegend=True,
            legend=dict(
                title="Metrics",
                orientation="v",
                yanchor="top",
                y=1.0,
                xanchor="left",
                x=1.01,
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="rgba(0,0,0,0.2)",
                borderwidth=1,
            ),
            margin=dict(r=200),
        )
        generated_plots[plot_name] = fig

        filter_options = {"METRIC": sorted(cols_to_plot)}
        if id_col:
            filter_options[id_col] = sorted(df[id_col].unique().tolist())

        if filter_options:
            filters_with_hints = {}
            for key, values in filter_options.items():
                source_property = "legendgroup" if (id_col and key == id_col) else "name"
                filters_with_hints[key] = {
                    "values": values,
                    "sample": values[:3],
                    "count": len(values),
                    "source": source_property,
                }
            generated_filters[f"{plot_name}_filters"] = filters_with_hints

    return generated_plots, generated_filters
