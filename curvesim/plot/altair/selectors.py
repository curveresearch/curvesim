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
    title = title or ""
    labels = labels or options

    init_sel = get_initial_selection(field, options, sel_idx)
    selector = selection_point(
        fields=[field], clear=False, value=init_sel, toggle=toggle
    )

    sel_chart = make_selector_chart(field, options, labels, selector, style)

    return sel_chart.properties(title=title), selector


def get_initial_selection(field, options, sel_idx):
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
    return condition(
        f"indexof({selector.name}.{field}, '{selected}') != -1", if_true, if_false
    )
