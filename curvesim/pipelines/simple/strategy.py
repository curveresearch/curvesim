from typing import Type

from curvesim.logging import get_logger
from curvesim.metrics.state_log import StateLog
from curvesim.templates import Log, Strategy, Trader

from .trader import SimpleArbitrageur

logger = get_logger(__name__)


class SimpleStrategy(Strategy):  # pylint: disable=too-few-public-methods
    """
    Class Attributes
    ----------------
    trader_class : :class:`~curvesim.pipelines.simple.trader.SimpleArbitrageur`
        Class for creating trader instances.
    state_log_class : :class:`~curvesim.metrics.StateLog`
        Class for creating state logger instances.
    """

    trader_class: Type[Trader] = SimpleArbitrageur
    log_class: Type[Log] = StateLog

    def _get_trader_inputs(self, sample):
        return (sample.prices,)
