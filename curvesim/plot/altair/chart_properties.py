from copy import deepcopy
from functools import partial

from altair import Color, MarkDef, X, Y


def make_chart_kwargs(default, override_dicts):
    chart_kwargs = deepcopy(default)

    for d in override_dicts:
        for key, val in d.items():
            update = UPDATE_RULES.get(key, update_properties)
            update(chart_kwargs, key, val)

    return init_properties(chart_kwargs)


def update_properties(prop_dict, key, val, depth=0, count=0):
    if depth in [0, count]:
        prop_dict[key] = val
    else:
        prop_dict.setdefault(key, {})
        for k, v in val.items():
            update_properties(prop_dict[key], k, v, depth, count + 1)


def concat_properties(prop_dict, key, val):
    prop_dict.setdefault(key, [])

    if isinstance(val, list):
        prop_dict[key] += val
    else:
        prop_dict[key].append(val)


def ignore_property(prop_dict, key, val):  # pylint: disable=unused-argument
    pass


def init_properties(prop_dict, classes=None):
    classes = classes or PROPERTY_CLASSES
    for key, val in prop_dict.items():
        try:
            prop_class = classes[key]
        except KeyError:
            continue

        if isinstance(prop_class, dict):
            prop_dict[key] = init_properties(val, classes=classes[key])
        else:
            prop_dict[key] = prop_class(**val)

    return prop_dict


PROPERTY_CLASSES = {
    "encoding": {
        "x": X,
        "y": Y,
        "color": Color,
    },
    "mark": MarkDef,
}

UPDATE_RULES = {
    "mark": partial(update_properties, depth=1),
    "encoding": partial(update_properties, depth=2),
    "selection": update_properties,
    "transform": concat_properties,
    "resample": ignore_property,
    "style": ignore_property,
}
