from altair import (
    Color,
    CalculateTransform,
    FilterTransform,
    Scale,
    concat,
    hconcat,
)

from ..selectors import make_selector


def make_result_selectors(factors, dynamic_axes):
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
    factor_names = list(factors.keys())

    charts = []
    transforms = []
    for idx, axis in enumerate(dynamic_axes):
        chart, transform = _make_axis_selector(axis, factor_names, idx)

        charts.append(chart)
        transforms.append(transform)

    return {"charts": charts, "transforms": transforms}


def make_parameter_filters(factors, dynamic_axes):
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
    left = concat(*axis_selector_charts, title="Axis Selectors:")
    right = concat(*parameter_filter_charts, title="Toggle Filters:")
    return hconcat(left, right.resolve_scale(color="independent"))
