from altair import concat, data_transformers, layer, value, vconcat

from ..make_chart import make_chart
from ..selectors import if_selected, make_selector
from .preprocessing import preprocess_data
from .result_selectors import make_result_selectors
from .tooltip import make_tooltip

data_transformers.disable_max_rows()


def make_page_from_results(results, data_key, axes, downsample=False):
    config = results.plot_config[data_key]
    factor_dict = results.factors
    factor_keys = list(factor_dict.keys())

    data_dict = make_data_dict(results, data_key, config, factor_keys, downsample)
    selectors = make_result_selectors(factor_dict, axes["dynamic"])
    return make_page(data_dict, config, factor_keys, axes["metric"], selectors)


def make_data_dict(results, data_key, config, factor_keys, downsample):
    columns = factor_keys + list(config.keys())
    data = getattr(results, data_key)(columns=columns)
    return preprocess_data(data, config, factor_keys, downsample)


def make_page(data_dict, config, factors, metric_axis, selectors):
    kwargs = selectors["kwargs"]
    charts = concat(data=data_dict["main"], columns=2)

    for metric_key, cfg in config.items():
        metrics, kwargs["data"] = get_metric_data(metric_key, data_dict)
        subplot = make_subplot(cfg, metrics, factors, metric_axis, kwargs)
        charts |= subplot

    page = vconcat(selectors["charts"], charts)
    return page.resolve_scale(color="independent")


def get_metric_data(metric_key, data_dict):
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
    if isinstance(metrics, list):
        make = make_layered_chart
    else:
        make = make_single_chart

    return make(config, metrics, metric_axis, factors, **kwargs)


def make_single_chart(config, metric, metric_axis, factors, **kwargs):
    kwargs[metric_axis] = metric
    chart = make_chart(config, **kwargs)
    tooltip = make_tooltip(chart["encoding"], metric_axis, factors)
    return chart.encode(tooltip=tooltip)


def make_layered_chart(config, metrics, metric_axis, factors, **kwargs):
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
