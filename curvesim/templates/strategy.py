from abc import ABC, abstractmethod
from typing import Optional, Type

from curvesim.logging import get_logger

from .log import Log
from .trader import Trader

logger = get_logger(__name__)


class Strategy(ABC):
    """
    A Strategy defines the trading approach used during each step of a simulation.
    It executes the trades using an injected `Trader` class and then logs the
    changes using the injected `Log` class.

    Class Attributes
    ----------------
    trader_class : :class:`~curvesim.templates.Trader`
        Class for creating trader instances.
    log_class : :class:`~curvesim.templates.Log`
        Class for creating log instances.

    Attributes
    ----------
    metrics : List[Metric]
        A list of metrics used to evaluate the performance of the strategy.
    """

    # These classes should be injected in child classes
    # to create the desired behavior.
    trader_class: Optional[Type[Trader]] = None
    log_class: Optional[Type[Log]] = None

    def __init__(self, metrics):
        """
        Parameters
        ----------
        metrics : List[Metric]
            A list of metrics used to evaluate the performance of the strategy.
        """
        self.metrics = metrics

    def __call__(self, pool, parameters, price_sampler):
        """
        Computes and executes trades at each timestep.

        Parameters
        ----------
        pool : :class:`~curvesim.pipelines.templates.SimPool`
            The pool to be traded against.

        parameters : dict
            Current pool parameters from the param_sampler (only used for
            logging/display).

        price_sampler : iterable
            Iterable that for each timestep returns market data used by
            the trader.


        Returns
        -------
        metrics : tuple of lists

        """
        # pylint: disable=not-callable
        trader = self.trader_class(pool)
        log = self.log_class(pool, self.metrics)

        parameters = parameters or "no parameter changes"
        logger.info("[%s] Simulating with %s", pool.symbol, parameters)

        pool.prepare_for_run(price_sampler.prices)

        for sample in price_sampler:
            pool.prepare_for_trades(sample.timestamp)
            trader_args = self._get_trader_inputs(sample)
            trade_data = trader.process_time_sample(*trader_args)
            log.update(price_sample=sample, trade_data=trade_data)

        return log.compute_metrics()

    @abstractmethod
    def _get_trader_inputs(self, sample):
        """
        Process the price sample into appropriate inputs for the
        trader instance.
        """
        raise NotImplementedError
