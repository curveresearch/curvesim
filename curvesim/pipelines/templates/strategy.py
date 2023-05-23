from abc import ABC, abstractmethod

from curvesim.logging import get_logger

logger = get_logger(__name__)


class Strategy(ABC):

    arbitrageur_class = None
    state_log_class = None

    def __init__(self, metrics):
        self.metrics = metrics

    def __call__(self, pool, parameters, price_sampler):
        """
        Computes and executes volume-limited arbitrage trades at each timestep.

        Parameters
        ----------
        pool : Pool, MetaPool, or RaiPool
            The pool to be arbitraged.

        parameters : dict
            Current pool parameters from the param_sampler (only used for logging/display).

        price_sampler : iterable
            Iterable to returns prices and volumes for each timestep.

        vol_mult : float or numpy.ndarray
            Value(s) multiplied by market volume to specify volume limits.

            Can be a scalar or vector with values for each pairwise coin combination.

        Returns
        -------
        metrics : tuple of lists

        """
        trader = self.arbitrageur_class(pool)  # noqa
        state_log = self.state_log_class(pool, self.metrics)

        symbol = pool.symbol
        logger.info(f"[{symbol}] Simulating with {parameters}")

        for sample in price_sampler:
            pool.prepare_for_trades(sample.timestamp)
            trader_args = self._get_trader_inputs(sample)
            trade_data = trader.arb_pool(*trader_args)
            state_log.update(price_sample=sample, trade_data=trade_data)

        return state_log.compute_metrics()

    @abstractmethod
    def _get_trader_inputs(self, sample):
        """
        Process the price sample into appropriate inputs for the
        arbitrageur instance.
        """
        raise NotImplementedError
