from curvesim.logging import get_logger
from curvesim.metrics.state_log import StateLog
from curvesim.pipelines.templates import Strategy
from curvesim.pipelines.vol_limited_arb.trader import VolumeLimitedArbitrageur

logger = get_logger(__name__)


class VolumeLimitedStrategy(Strategy):

    trader_class = VolumeLimitedArbitrageur
    state_log_class = StateLog

    def __init__(self, metrics, vol_mult=None):
        super().__init__(metrics)
        self.vol_mult = vol_mult

    def _get_trader_inputs(self, sample):
        volume_limits = sample.volumes * self.vol_mult
        return sample.prices, volume_limits
