from pandas import DataFrame, concat

from curvesim.metrics.base import PoolMetric
from .pool_parameters import get_pool_parameters
from .pool_state import get_pool_state


class StateLog:
    """
    Unified logger to store the metrics specified for a simulation.
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
        self.state_per_trade.append({"pool_state": get_pool_state(self.pool), **kwargs})

    def get_logs(self):
        df = DataFrame(self.state_per_trade)
        state_per_trade = {col: DataFrame(df[col].to_list()) for col in df}
        return {**self.state_per_run, **state_per_trade}

    def compute_metrics(self):
        state_logs = self.get_logs()
        metric_data = [metric.compute(state_logs) for metric in self.metrics]
        data_per_trade, summary_data = tuple(zip(*metric_data))  # transpose tuple list

        return (
            DataFrame(self.state_per_run, index=[0]),
            concat(data_per_trade, axis=1),
            concat(summary_data, axis=1),
        )


def prepare_metrics(metrics, pool):
    for metric in metrics:
        if isinstance(metric, PoolMetric):
            metric.set_pool(pool)
    return metrics
