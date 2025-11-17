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
    It intelligently splits metrics and handles unit conversions for memory.
    """
    generated_plots: Dict[str, Figure] = {}
    generated_filters: Dict[str, Dict] = {}

    y_axis_unit_label = "Value"
    if name == "sar_memory":
        kb_columns = [col for col in df.columns if col.startswith("kb")]
        for col in kb_columns:
            gb_col_name = col.replace("kb", "") + "_gb"
            if col in df:
                df[gb_col_name] = df[col] / (1024 * 1024)

        value_cols_to_plot = [col.replace("kb", "") + "_gb" for col in kb_columns]
        df_to_plot = df
        y_axis_unit_label = "Memory (GB)"
    else:
        value_cols_to_plot = [c for c in df.columns if df[c].dtype.kind in "if" and c not in ["interval", "hostname"]]
        df_to_plot = df

    percent_cols = [c for c in value_cols_to_plot if "%" in c]
    absolute_cols = [c for c in value_cols_to_plot if c not in percent_cols]

    id_col = next((col for col in ["IFACE", "DEV", "cpu"] if col in df_to_plot.columns), None)

    metric_groups = {}
    if percent_cols:
        metric_groups["percent"] = percent_cols
    if absolute_cols:
        metric_groups["absolute"] = absolute_cols

    for metric_type, cols_to_plot in metric_groups.items():
        if not cols_to_plot:
            continue

        plot_name = f"{name}_{metric_type}" if len(metric_groups) > 1 else name

        valid_cols_to_plot = [c for c in cols_to_plot if c in df_to_plot.columns]
        if not valid_cols_to_plot:
            continue

        melted_df = df_to_plot.melt(
            id_vars=["timestamp"] + ([id_col] if id_col else []),
            value_vars=valid_cols_to_plot,
            var_name="metric",
            value_name="value",
        )
        if melted_df.empty:
            continue

        chart_title = f"{name.replace('_', ' ').title()} Metrics"
        y_axis_title = y_axis_unit_label if metric_type == "absolute" else "Percentage (%)"
        if name == "sar_load":
            chart_title = "System Load & Run Queue Length"

        if len(metric_groups) > 1:
            chart_title += " (Percentages)" if metric_type == "percent" else " (Absolute Values)"

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

        filter_options = {"METRIC": sorted(valid_cols_to_plot)}
        if id_col:
            filter_options[id_col] = sorted(df_to_plot[id_col].unique().tolist())

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
