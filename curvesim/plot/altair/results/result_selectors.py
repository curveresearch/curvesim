"""
This module provides functionality for creating result selectors for an Altair
chart.

It contains utility functions for creating axis selectors, parameter filters,
selector charts and result selectors.
"""

from altair import CalculateTransform, Color, FilterTransform, Scale, concat, hconcat

from ..selectors import make_selector


def make_result_selectors(factors, dynamic_axes):
    """
    Creates result selectors for an Altair chart.

    Parameters
    ----------
    factors : dict
        The factors to create selectors for.
    dynamic_axes : dict
        The dynamic axes to create selectors for.

    Returns
    -------
    dict
        Keyword arguments to add selections to metric charts and chart objects to
        display the selectors.
    """
    dynamic_axes = dict(list(dynamic_axes.items())[: len(factors)])

    axes = make_axis_selectors(factors, dynamic_axes)
    parameters = make_parameter_filters(factors, dynamic_axes)

    # kwargs to pass to metric charts
    metric_kwargs = {
        axis: {"shorthand": shorthand, "title": None}
        for axis, shorthand in dynamic_axes.items()
    }
    metric_kwargs["transform"] = axes["transforms"] + parameters["transforms"]

    return {
        "kwargs": metric_kwargs,
        "charts": format_selector_charts(axes["charts"], parameters["charts"]),
    }


def make_axis_selectors(factors, dynamic_axes):
    """
    Creates axis selectors.

    Parameters
    ----------
    factors : dict
        The factors to use as selector options.
    dynamic_axes : dict
        The dynamic axes to create selectors for.

    Returns
    -------
    dict
        The axis selectors and the charts to display them.
    """
    factor_names = list(factors.keys())

    charts = []
    transforms = []
    for idx, axis in enumerate(dynamic_axes):
        chart, transform = _make_axis_selector(axis, factor_names, idx)

        charts.append(chart)
        transforms.append(transform)

    return {"charts": charts, "transforms": transforms}


def make_parameter_filters(factors, dynamic_axes):
    """
    Creates parameter filters.

    Parameters
    ----------
    factors : dict
        The factors to create selectors for.
    dynamic_axes : dict
        The dynamic axes for a chart page. Used to determine initial selections.

    Returns
    -------
    dict
        The parameter filters and the charts to display them.
    """
    n_dynamic_axes = len(dynamic_axes)

    charts = []
    transforms = []
    for i, factor in enumerate(factors.items()):
        idx = "all" if i < n_dynamic_axes else 0
        chart, transform = _make_parameter_filter(*factor, idx)

        charts.append(chart)
        transforms.append(transform)

    return {"charts": charts, "transforms": transforms}


def _make_axis_selector(axis, options, sel_idx):
    """
    Makes a single axis selector.

    Parameters
    ----------
    axis : str
        The axis to create a selector for.
    options : list
        The options for the selector.
    sel_idx : int or 'all'
        The initial selection index. If an integer, select that option. If 'all',
        select all options.

    Returns
    -------
    altair.Chart, altair.CalculateTransform
        The axis selector chart and the transform for the selector.
    """
    chart, selector = make_selector(
        axis,
        options,
        title=axis,
        style={"axis": "y", "orient": "left"},
        toggle=False,
        sel_idx=sel_idx,
    )

    calc_kwargs = {"calculate": f"datum[{selector.name}.{axis}]", "as": axis}
    return chart, CalculateTransform(**calc_kwargs)


def _make_parameter_filter(factor, options, sel_idx):
    """
    Makes a single parameter filter.

    Parameters
    ----------
    factor : str
        The factor to create a filter for.
    options : list
        The options for the filter.
    sel_idx : int or 'all'
        The initial selection index. If an integer, select that option. If 'all',
        select all options.

    Returns
    -------
    altair.Chart, altair.FilterTransform
        The parameter filter chart and the filter transform.
    """
    color = Color("labels:O", scale=Scale(scheme="viridis"), legend=None)

    chart, selector = make_selector(
        factor,
        options,
        title=factor,
        style={"axis": "x", "orient": "bottom", "color": color},
        toggle="true",
        sel_idx=sel_idx,
    )
    return chart, FilterTransform(selector)


def format_selector_charts(axis_selector_charts, parameter_filter_charts):
    """
    Formats selector charts for display.

    Parameters
    ----------
    axis_selector_charts : list of altair.Chart
        The axis selector charts.
    parameter_filter_charts : list of altair.Chart
        The parameter filter charts.

    Returns
    -------
    altair.hconcat
        The formatted selector charts.
    """
    left = concat(*axis_selector_charts, title="Axis Selectors:")
    right = concat(*parameter_filter_charts, title="Toggle Filters:")
    return hconcat(left, right.resolve_scale(color="independent"))
