from altair import TitleParams, vconcat

from curvesim.plot.result_plotter import ResultPlotter
from curvesim.utils import override

from .make_page import make_page_from_results


def plot_results(results):
    """
    Takes a :class:`.metrics.SimResults` object and plots the data returned by both
    :func:`SimResults.summary` and :func:`SimResults.data`
    """

    summary = plot_summary(results)
    timeseries = plot_data(results)
    return vconcat(summary, timeseries).resolve_scale(color="independent")


def plot_summary(results):
    """
    Takes a :class:`.metrics.SimResults` object and plots the data returned by
    :func:`SimResults.summary`.
    """
    title = TitleParams(text="Summary Metrics", fontSize=16)
    data_key = "summary"
    axes = {"metric": "y", "dynamic": {"x": "x:Q", "color": "color:O"}}

    page = make_page_from_results(results, data_key, axes)
    return page.properties(title=title)


def plot_data(results):
    """
    Takes a :class:`.metrics.SimResults` object and plots the data returned by
    :func:`SimResults.data`.
    """
    title = TitleParams(text="Timeseries Data", fontSize=16)
    data_key = "data"
    axes = {"metric": "y", "dynamic": {"color": "color:O"}}

    page = make_page_from_results(results, data_key, axes, downsample=True)
    return page.properties(title=title)


class AltairResultPlotter(ResultPlotter):
    """
    :class:`.plot.ResultPlotter` implementation using Altair.
    """

    @override
    def save(self, chart, save_as):
        chart.save(save_as)


result_plotter = AltairResultPlotter(plot_data, plot_results, plot_summary)
