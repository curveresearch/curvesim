"""
This module provides functionality for preprocessing data for chart creation.

It contains utility functions for downsampling and preprocessing data, resampling data,
converting data to histograms, and creating histograms.
"""
from pandas import Grouper, Series, concat

from curvesim.exceptions import PlotError


def preprocess_data(data, config, factors, downsample=False):
    """
    Preprocesses data for chart creation, with an option to downsample.

    Parameters
    ----------
    data : pandas.DataFrame
        The data to preprocess.
    config : dict
        The plot configuration.
    factors : list
        The list of factors.
    downsample : bool, optional
        Whether to downsample the data. Defaults to False.

    Returns
    -------
    dict
        The preprocessed data dictionary.
    """
    if downsample:
        return downsample_data(data, config, factors)

    factor_data = data[factors]  # preserve unrounded factors
    data_out = data.round(6)
    data_out[factors] = factor_data
    return {"main": data_out}


def downsample_data(data, config, factors):
    """
    Downscales the data according to provided configurations and factors.

    Parameters
    ----------
    data : pandas.DataFrame
        The data to downsample.
    config : dict
        The plot configuration.
    factors : list
        The list of factors.

    Returns
    -------
    dict
        The downsampled data dictionary.

    Raises
    ------
    PlotError
        If no resample strategy is found in the configuration for a metric.
    """
    data_out = {}
    resample = {"run": "last"}
    for metric, cfg in config.items():
        rule = cfg.get("resample")

        if rule:
            resample[metric] = rule

        elif rule is False:
            data_out[metric] = data.pop(metric)

        elif cfg["style"].startswith("histogram"):
            d = concat([data[factors], data.pop(metric)], axis=1)
            data_out[metric] = to_histograms(d, factors)

        else:
            raise PlotError(f"No resample strategy found in {metric} config.")

    data_out["main"] = resample_data(data, factors, resample)
    return data_out


def resample_data(data, factors, fns):
    """
    Resamples the data based on the provided factors and resampling functions.

    Parameters
    ----------
    data : pandas.DataFrame
        The data to resample.
    factors : list
        The list of factors.
    fns : dict
        The resampling functions.

    Returns
    -------
    pandas.DataFrame
        The resampled data.
    """
    groups = factors + [Grouper(freq="1D", key="timestamp")]
    resampled = data.groupby(groups).agg(fns).round(6)
    return resampled.reset_index()


def to_histograms(data, factors):
    """
    Converts the data to histograms.

    Parameters
    ----------
    data : pandas.DataFrame
        The data to convert.
    factors : list
        The list of factors.

    Returns
    -------
    pandas.DataFrame
        The data converted to histograms.
    """
    if not factors:
        return make_histogram(data).reset_index()

    return data.groupby(factors).apply(make_histogram).reset_index()


def make_histogram(data, bins=500):
    """
    Creates a histogram from the data.

    Parameters
    ----------
    data : pandas.DataFrame
        The data to create a histogram from.
    bins : int, optional
        The number of bins for the histogram. Defaults to 500.

    Returns
    -------
    pandas.Series
        The histogram.
    """
    metric = data.iloc[:, -1]
    minimum = Series(0, index=[metric.min()])

    hist = metric.value_counts(bins=bins, sort=False, normalize=True)
    hist.index = hist.index.right
    hist = concat([minimum, hist])
    hist.index.name, hist.name = metric.name, "frequency"
    return hist.round(6)
