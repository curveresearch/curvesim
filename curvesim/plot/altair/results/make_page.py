"""
This module provides functionality for creating interactive Altair charts from
simulation results.

It contains utility functions for creating data dictionaries, pages, subplots,
and layered or single charts. It uses selectors to control chart properties and
apply tooltips.
"""
from altair import concat, data_transformers, layer, value, vconcat

from ..make_chart import make_chart
from ..selectors import if_selected, make_selector
from .preprocessing import preprocess_data
from .result_selectors import make_result_selectors
from .tooltip import make_tooltip

data_transformers.disable_max_rows()


def make_page_from_results(results, data_key, axes, downsample=False):
    """
    Creates an interactive Altair chart from simulation results.

    Parameters
    ----------
    results : Results
        The simulation results.
    data_key : str
        The key to retrieve data from the results.
    axes : dict
        The axes configuration.
    downsample : bool, optional
        Whether to downsample the data. Defaults to False.

    Returns
    -------
    altair.vconcat
        The created chart page.
    """
    config = results.plot_config[data_key]
    factor_dict = results.factors
    factor_keys = list(factor_dict.keys())

    data_dict = make_data_dict(results, data_key, config, factor_keys, downsample)
    selectors = make_result_selectors(factor_dict, axes["dynamic"])
    return make_page(data_dict, config, factor_keys, axes["metric"], selectors)


def make_data_dict(results, data_key, config, factor_keys, downsample):
    """
    Prepares the data from the results for chart creation.

    Parameters
    ----------
    results : Results
        The simulation results.
    data_key : str
        The key to retrieve data from the results.
    config : dict
        The plot configuration.
    factor_keys : list
        The keys for the factors.
    downsample : bool
        Whether to downsample the data.

    Returns
    -------
    dict
        The data dictionary.
    """
    columns = factor_keys + list(config.keys())
    data = getattr(results, data_key)(columns=columns)
    return preprocess_data(data, config, factor_keys, downsample)


def make_page(data_dict, config, factors, metric_axis, selectors):
    """
    Creates an interactive Altair chart page with multiple subplots.

    Parameters
    ----------
    data_dict : dict
        The data dictionary.
    config : dict
        The plot configuration.
    factors : list
        The list of factors.
    metric_axis : str
        The axis for the metrics.
    selectors : dict
        The selectors configuration.

    Returns
    -------
    altair.vconcat
        The created chart page.
    """
    kwargs = selectors["kwargs"]
    page = concat(data=data_dict["main"], columns=2)

    for metric_key, cfg in config.items():
        metrics, kwargs["data"] = get_metric_data(metric_key, data_dict)
        subplot = make_subplot(cfg, metrics, factors, metric_axis, kwargs)
        page |= subplot

    if factors:
        page = vconcat(selectors["charts"], page)

    return page.resolve_scale(color="independent")


def get_metric_data(metric_key, data_dict):
    """
    Retrieves the relevant data for a specific metric.

    Parameters
    ----------
    metric_key : str
        The key for the metric.
    data_dict : dict
        The data dictionary.

    Returns
    -------
    str or list of str, pandas.DataFrame
        The metrics and the data for the metrics.
    """
    if metric_key in data_dict:
        data = data_dict[metric_key]
    else:
        data = data_dict["main"]

    submetrics = [c for c in data if c.startswith(metric_key + " ")]
    n_submetrics = len(submetrics)

    if n_submetrics == 0:
        return metric_key, data

    if n_submetrics == 1:
        return submetrics[0], data

    return submetrics, data


def make_subplot(config, metrics, factors, metric_axis, kwargs):
    """
    Creates a subplot for a specific metric.

    Parameters
    ----------
    config : dict
        The plot configuration.
    metrics : str or list of str
        The metric or metrics.
    factors : list
        The list of factors.
    metric_axis : str
        The axis for the metrics.
    kwargs : dict
        Additional keyword arguments.

    Returns
    -------
    altair.vconcat
        The created subplot.
    """
    if isinstance(metrics, list):
        make = make_layered_chart
    else:
        make = make_single_chart

    return make(config, metrics, metric_axis, factors, **kwargs)


def make_single_chart(config, metric, metric_axis, factors, **kwargs):
    """
    Creates a single chart for a specific metric.

    Parameters
    ----------
    config : dict
        The plot configuration.
    metric : str
        The metric.
    metric_axis : str
        The axis for the metrics.
    factors : list
        The list of factors.
    **kwargs
        Additional keyword arguments.

    Returns
    -------
    altair.Chart
        The created chart.
    """
    kwargs[metric_axis] = metric
    chart = make_chart(config, **kwargs)
    tooltip = make_tooltip(chart["encoding"], metric_axis, factors)
    return chart.encode(tooltip=tooltip)


def make_layered_chart(config, metrics, metric_axis, factors, **kwargs):
    """
    Creates a layered chart for multiple submetrics of a metric.

    Parameters
    ----------
    config : dict
        The plot configuration.
    metrics : list of str
        The metrics.
    metric_axis : str
        The axis for the metrics.
    factors : list
        The list of factors.
    **kwargs
        Additional keyword arguments.

    Returns
    -------
    altair.vconcat
        The created chart.
    """
    labels = [metric.split(" ")[1].capitalize() for metric in metrics]
    sel_chart, selector = make_selector(
        "submetric", metrics, labels=labels, toggle="true", sel_idx=0
    )

    chart = layer()
    for submetric, label in zip(metrics, labels):
        kwargs[metric_axis] = submetric
        _layer = make_chart(config, **kwargs)
        tooltip = make_tooltip(_layer["encoding"], metric_axis, factors, prefix=label)
        opacity = if_selected(submetric, selector, "submetric", value(1), value(0))
        chart += _layer.encode(tooltip=tooltip, opacity=opacity)
    return vconcat(chart, sel_chart, spacing=2)
