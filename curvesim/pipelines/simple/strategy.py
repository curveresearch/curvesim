from curvesim.logging import get_logger
from curvesim.metrics.state_log import StateLog
from curvesim.pipelines.templates import Strategy

from .trader import SimpleArbitrageur

logger = get_logger(__name__)


class SimpleStrategy(Strategy):

    trader_class = SimpleArbitrageur
    state_log_class = StateLog

    def _get_trader_inputs(self, sample):
        return (sample.prices,)
