"""
This module provides functionality for creating Altair charts with custom styles.

It contains utility functions for creating charts and default chart properties. It
uses styles defined in the .styles module and allows custom configuration of chart
properties.
"""
from altair import Chart, Scale, data_transformers

from curvesim.exceptions import PlotError

from .chart_properties import make_chart_kwargs
from .styles import STYLES

data_transformers.disable_max_rows()


def make_chart(config, x=None, y=None, color=None, **kwargs):
    """
    Create an interactive chart with custom properties and styles.

    Parameters
    ----------
    config : dict
        The configuration dictionary for the chart. Must contain a 'style' key.
    x : str or dict, optional
        The x-axis property. Can be a shorthand string or a dictionary
        of alt.X kwargs.
    y : str or dict, optional
        The y-axis property. Can be a shorthand string or a dictionary
        of alt.Y kwargs.
    color : str or dict, optional
        The color property. Can be a shorthand string or a dictionary
        of alt.Color kwargs.
    **kwargs
        Additional keyword arguments are added to the chart configuration.

    Returns
    -------
    altair.Chart
        The created chart.

    Raises
    ------
    PlotError
        If no style is found in the config or if the style is not found in STYLES.
    """
    title = config.get("title", "")

    try:
        style = config["style"]
    except KeyError as e:
        raise PlotError(f"No style found in {title} config.") from e

    try:
        style = STYLES[style]
    except KeyError as e:
        raise PlotError(f"Style {style} not found in plot.styles.") from e

    defaults = make_defaults(title, x, y, color)
    chart_kwargs = make_chart_kwargs(defaults, [style, config, kwargs])
    return Chart(**chart_kwargs).interactive()


def make_defaults(title, x=None, y=None, color=None):
    """
    Create default properties for a chart.

    Parameters
    ----------
    title : str
        The title of the chart.
    x : str or dict, optional
        The x-axis property. Can be a shorthand string or a dictionary
        of alt.X kwargs.
    y : str or dict, optional
        The y-axis property. Can be a shorthand string or a dictionary
        of alt.Y kwargs.
    color : str or dict, optional
        The color property. Can be a shorthand string or a dictionary
        of alt.Color kwargs.

    Returns
    -------
    dict
        The default properties for a chart.

    Raises
    ------
    PlotError
        If x, y, or color is not a string (shorthand) or
        a dictionary (altair kwargs).
    """
    defaults = {
        "title": title,
        "encoding": {
            "x": {},
            "y": {"title": title},
            "color": {"scale": Scale(scheme="viridis")},
        },
    }

    for key, val in zip(["x", "y", "color"], [x, y, color]):
        if val:
            if isinstance(val, str):
                val = {"shorthand": val}

            elif not isinstance(val, dict):
                cap = key.capitalize()
                raise PlotError(
                    f"{key} must be a string (shorthand) or dict (alt.{cap} kwargs)."
                )

            for k, v in val.items():
                defaults["encoding"][key][k] = v

    return defaults
