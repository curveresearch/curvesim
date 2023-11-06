from typing import Type

from curvesim.logging import get_logger
from curvesim.metrics.state_log.log import StateLog
from curvesim.pipelines.vol_limited_arb.trader import VolumeLimitedArbitrageur
from curvesim.templates import Log, Strategy, Trader

logger = get_logger(__name__)


class VolumeLimitedStrategy(Strategy):
    """
    Computes and executes volume-limited arbitrage trades at each timestep.
    """

    trader_class: Type[Trader] = VolumeLimitedArbitrageur
    log_class: Type[Log] = StateLog

    def __init__(self, metrics, vol_mult):
        """
        Parameters
        -----------
        metrics : List[Metric]
            A list of metrics used to evaluate the performance of the strategy.
        vol_mult : float or numpy.ndarray
            Value(s) multiplied by market volume to specify volume limits.

            Can be a scalar or vector with values for each pairwise coin combination.
        """
        super().__init__(metrics)
        self.vol_mult = vol_mult

    def _get_trader_inputs(self, sample):  # pylint: disable=too-few-public-methods
        volume_limits = _compute_volume_limits(sample, self.vol_mult)
        return sample.prices, volume_limits


def _compute_volume_limits(sample, vol_mult):
    prices = sample.prices
    volumes = sample.volumes

    limits = {key: volumes[key] * vol_mult[key] for key in volumes}
    reversed_limits = {(j, i): lim * prices[(i, j)] for (i, j), lim in limits.items()}
    all_limits = {**limits, **reversed_limits}

    return {key: int(val * 10**18) for key, val in all_limits.items()}
