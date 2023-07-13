"""
This module provides functionality for creating interactive selector charts with
Altair and pandas.

It contains utility functions for creating selector charts, initializing selectors,
manipulating opacity of selections, and conditionally applying properties.
"""
from altair import Axis, Chart, Color, Scale, condition, selection_point, value
from pandas import DataFrame

from curvesim.exceptions import PlotError

from .chart_properties import PROPERTY_CLASSES


def make_selector(
    field,
    options,
    *,
    labels=None,
    title=None,
    style=None,
    toggle=True,
    sel_idx=None,
):
    """
    Create an interactive selector chart and an Altair selection object.

    Parameters
    ----------
    field : str
        The field in the data to bind the selection to.
    options : list
        The options for the selection.
    labels : list, optional
        The labels for the options. Defaults to the options themselves.
    title : str, optional
        The title of the chart. Defaults to an empty string.
    style : dict, optional
        A dictionary of style options to update the default style with.
    toggle : bool, optional
        Whether to allow toggle behavior in the selection. Defaults to True.
    sel_idx : int or 'all', optional
        The initial selection index. If an integer, select that option. If 'all',
        select all options. If None, no initial selection. Defaults to None.

    Returns
    -------
    altair.Chart
        The created selector chart.
    altair.Selection
        The created selection object.

    Raises
    ------
    PlotError
        If sel_idx is not None, an integer, or 'all'.
    """
    title = title or ""
    labels = labels or options

    init_sel = get_initial_selection(field, options, sel_idx)
    selector = selection_point(
        fields=[field], clear=False, value=init_sel, toggle=toggle
    )

    sel_chart = make_selector_chart(field, options, labels, selector, style)

    return sel_chart.properties(title=title), selector


def get_initial_selection(field, options, sel_idx):
    """
    Get the initial selection value based on provided options and an index.

    Parameters
    ----------
    field : str
        The field in the data to bind the selection to.
    options : list
        The options for the selection.
    sel_idx : int or 'all', optional
        The initial selection index. If an integer, select that option. If 'all',
        select all options. If None, no initial selection.

    Returns
    -------
    dict or list of dict or None
        The initial selection value. If sel_idx is an integer, a dictionary. If 'all',
        a list of dictionaries. If None, None.

    Raises
    ------
    PlotError
        If sel_idx is not None, an integer, or 'all'.
    """
    if sel_idx is None:
        init_sel = None

    elif isinstance(sel_idx, int):
        init_sel = [{field: options[sel_idx]}]

    elif sel_idx == "all":
        init_sel = [{field: o} for o in options]

    else:
        raise PlotError(f"sel_idx must be None or int or 'all', not {type(sel_idx)}.")

    return init_sel


def make_selector_chart(field, options, opt_labels, selector, style=None):
    """
    Create the selector chart.

    Parameters
    ----------
    field : str
        The field in the data to bind the selection to.
    options : list
        The options for the selection.
    opt_labels : list
        The labels for the options.
    selector : altair.Selection
        The selector to add to the chart.
    style : dict, optional
        A dictionary of style options to update the default style with.

    Returns
    -------
    altair.Chart
        The created selector chart.
    """
    _style = {
        "axis": "y",
        "orient": "right",
        "color": Color(scale=Scale(scheme="viridis"), legend=None),
    }

    if style:
        _style.update(style)

    axis = _style["axis"]
    orient = _style["orient"]
    axis_class = PROPERTY_CLASSES["encoding"][axis]

    encoding = {
        axis: axis_class("labels:O", title=None, axis=Axis(orient=orient)),
        "color": _style["color"],
        "opacity": condition(selector, value(1), value(0.1)),
    }

    df = DataFrame({field: options, "labels": opt_labels})
    return Chart(df).mark_rect().encode(**encoding).add_params(selector)


def if_selected(selected, selector, field, if_true, if_false):
    """
    Apply a property if a selection is active.

    Parameters
    ----------
    selected : any
        The selected value.
    selector : altair.Selection
        The selector to check.
    field : str
        The field in the data to check the selection against.
    if_true : any
        The value to return if the selection is active.
    if_false : any
        The value to return if the selection is not active.

    Returns
    -------
    altair.condition
        The condition to apply to a chart.
    """
    return condition(
        f"indexof({selector.name}.{field}, '{selected}') != -1", if_true, if_false
    )
