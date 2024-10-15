"""
This module provides functionality for creating and manipulating chart properties.

It contains utility functions for creating keyword arguments for a chart, updating
and initializing chart properties, and handling property-specific behaviors.
"""
from copy import deepcopy
from functools import partial

from altair import Color, MarkDef, X, Y


def make_chart_kwargs(default, override_dicts):
    """
    Create the keyword arguments for a chart by updating a default dictionary with
    values from a list of override dictionaries.

    Parameters
    ----------
    default : dict
        The default keyword arguments for the chart.
    override_dicts : list
        A list of dictionaries containing addtional keyword arguments and/or overrides
        for the default keyword arguments.

    Returns
    -------
    dict
        A dictionary containing the keyword arguments for the chart.
    """
    chart_kwargs = deepcopy(default)

    for d in override_dicts:
        for key, val in d.items():
            update = UPDATE_RULES.get(key, update_properties)
            update(chart_kwargs, key, val)

    return init_properties(chart_kwargs)


def update_properties(prop_dict, key, val, depth=0, count=0):
    """
    Update properties in a dictionary. If the current depth matches the target depth,
    the value is updated directly. Otherwise, the function is called recursively on
    nested dictionaries.

    Parameters
    ----------
    prop_dict : dict
        The dictionary of properties to update.
    key : str
        The key of the property to update.
    val : any
        The new value for the property.
    depth : int, optional
        The target depth for the update. Defaults to 0.
    count : int, optional
        The current depth of the update. Defaults to 0.
    """

    if depth in [0, count]:
        prop_dict[key] = val
    else:
        prop_dict.setdefault(key, {})
        for k, v in val.items():
            update_properties(prop_dict[key], k, v, depth, count + 1)


def concat_properties(prop_dict, key, val):
    """
    Concatenate values to a property in a dictionary. If the value is a list, extend
    the property with it. Otherwise, append the value to the property.

    Parameters
    ----------
    prop_dict : dict
        The dictionary of properties to update.
    key : str
        The key of the property to update.
    val : any
        The value to concatenate to the property.
    """
    prop_dict.setdefault(key, [])

    if isinstance(val, list):
        prop_dict[key] += val
    else:
        prop_dict[key].append(val)


def ignore_property(prop_dict, key, val):  # pylint: disable=unused-argument
    """
    Ignore a property during an update operation. This function does nothing and is
    intended to be used as a placeholder in UPDATE_RULES where certain properties
    should be ignored.

    Parameters
    ----------
    prop_dict : dict
        The dictionary of properties to update.
    key : str
        The key of the property to ignore.
    val : any
        The value of the property to ignore.
    """


def init_properties(prop_dict, classes=None):
    """
    Initialize the properties of a dictionary using a mapping of classes. If a
    property's key is present in the classes dictionary, its value is replaced
    with an instance of the corresponding class, initialized with the value as
    keyword arguments.

    Parameters
    ----------
    prop_dict : dict
        The dictionary of properties to initialize.
    classes : dict, optional
        A dictionary mapping keys to classes. If a key in prop_dict matches a
        key in classes, the value in prop_dict is replaced with an instance of
        the corresponding class. Defaults to PROPERTY_CLASSES.

    Returns
    -------
    dict
        The dictionary of properties, with values replaced with class instances
        where applicable.
    """
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
