from typing import List, Optional
import plotly.graph_objects as go


def make_single_plot(
    scatters: List[go.Scatter],
    title: str,
    xaxis_title: str,
    yaxis_title: str,
    show: bool = True,
    write_to_html: Optional[str] = None,
) -> go.Figure:
    """Make single plotly graph based on the list of scatters.

    Args:
        scatters (List[go.Scatter]): Scsatters to plot.
        title (str): Title of the plot.
        xaxis_title (str): Title of the x-axis.
        yaxis_title (str): Title of the y-axis.
        show (bool, optional): Whether to show the fig directly. Defaults to True.
        write_to_html (Optional[str], optional): If specified, will write fig to the path with html format. Defaults to None.

    Returns:
        go.Figure: The plotly figure.
    """
    fig = go.Figure()
    for s in scatters:
        fig.add_trace(s)
    fig.update_layout(
        title=title,
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        hovermode="closest",
    )
    if show:
        fig.show()
    if write_to_html:
        fig.write_html(write_to_html)
    return fig
