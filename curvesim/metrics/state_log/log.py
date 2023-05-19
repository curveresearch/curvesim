from pandas import DataFrame, concat

from curvesim.metrics.base import PoolMetric
from .pool_parameters import get_pool_parameters
from .pool_state import get_pool_state


class StateLog:
    """
    Logger that records simulation/pool state throughout each simulation run and
    computes metrics at the end of each run.
    """

    __slots__ = [
        "metrics",
        "pool",
        "state_per_run",
        "state_per_trade",
    ]

    def __init__(self, pool, metrics):
        self.pool = pool
        self.metrics = prepare_metrics(metrics, pool)
        self.state_per_run = get_pool_parameters(pool)
        self.state_per_trade = []

    def update(self, **kwargs):
        """Records pool state and any keyword arguments provided."""

        self.state_per_trade.append({"pool_state": get_pool_state(self.pool), **kwargs})

    def get_logs(self):
        """Returns the accumulated log data."""

        df = DataFrame(self.state_per_trade)
        state_per_trade = {col: DataFrame(df[col].to_list()) for col in df}
        return {**self.state_per_run, **state_per_trade}

    def compute_metrics(self):
        """Computes metrics from the accumulated log data."""

        state_logs = self.get_logs()
        metric_data = [metric.compute(state_logs) for metric in self.metrics]
        data_per_trade, summary_data = tuple(zip(*metric_data))  # transpose tuple list

        return (
            DataFrame(self.state_per_run, index=[0]),
            concat(data_per_trade, axis=1),
            concat(summary_data, axis=1),
        )


def prepare_metrics(metrics, pool):
    """
    Applies any neccessary preparations to the input metrics.
    Currently, only updates the pool object for PoolMetrics.
    """
    for metric in metrics:
        if isinstance(metric, PoolMetric):
            metric.set_pool(pool)
    return metrics
