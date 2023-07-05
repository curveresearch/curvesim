from curvesim.logging import get_logger
from curvesim.metrics.state_log import StateLog
from curvesim.pipelines.vol_limited_arb.trader import VolumeLimitedArbitrageur
from curvesim.templates import Strategy

logger = get_logger(__name__)


class VolumeLimitedStrategy(Strategy):
    """
    Computes and executes volume-limited arbitrage trades at each timestep.
    """

    trader_class = VolumeLimitedArbitrageur
    state_log_class = StateLog

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

    def _get_trader_inputs(self, sample):
        volume_limits = compute_volume_limits(sample.volumes, self.vol_mult)
        return sample.prices, volume_limits


def compute_volume_limits(volumes, vol_mult):
    limits = {key: volumes[key] * vol_mult[key] for key in volumes}
    reversed_limits = {(j, i): lim for (i, j), lim in limits.items()}
    return {**limits, **reversed_limits}
