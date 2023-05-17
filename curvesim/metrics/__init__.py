"""
Metrics recorded during simulations. The submodule includes:

    1. **Metric objects:**
        Objects that compute and record metrics/statistics throughout simulations,
        and provide a config attribute that specifies how to compute, summarize, and/or
        plot the recorded data.

        :mod:`.metrics.base` contains the metrics base class and generic metric classes.

        :mod:`.metrics.metrics` contains specific metric classes for use in simulations.

    2. :class:`.StateLog`:
        Logger that records simulation/pool state throughout a simulation and computes
        metrics at the end of each simulation run.

    3. :class:`.SimResults`:
        Container for simulation results with methods to plot or return recorded
        metrics as DataFrames.
"""

__all__ = ["SimResults", "StateLog", "init_metrics", "make_results", "metrics"]

from .state_log import StateLog
from .results import SimResults, make_results
from . import metrics


def init_metrics(metric_classes, **kwargs):
    """
    Initializes metric classes with **kwargs as keyword arguments. Each metric class
    only uses the keyword arguments specified in its __init__ method.

    Parameters
    ----------
    metric_classes : list
        A list of metric classes (e.g., from curvesim.metrics.metrics)

    kwargs :
        The keyword arguments used when initializing each metric class.

    Returns
    -------
    metrics :
        A list of the initialized metrics.
    """
    return [Metric(**kwargs) for Metric in metric_classes]
