"""
Functions and interfaces used in the simulation pipeline framework.
"""
import multiprocessing
from abc import ABC, abstractmethod
from logging.handlers import QueueListener
from multiprocessing import Pool as cpu_pool

from curvesim.logging import get_logger

logger = get_logger(__name__)


def run_pipeline(param_sampler, price_sampler, strategy, ncpu=4, logging_queue=None):
    """
    Core function for running pipelines.

    Typically called within a function specifying the pipeline components
    (see, e.g., :func:`.volume_limited_arbitrage()`)

    Parameters
    ----------
    param_sampler : iterator
        An iterator that returns pool parameters (see :mod:`.param_samplers`).

    price_sampler : iterator
        An iterator that returns (minimally) a time-series of prices
        (see :mod:`.price_samplers`).

    strategy: callable
        A function dictating what happens at each timestep.

    ncpu : int, default=4
        Number of cores to use.

    Returns
    -------
    results : tuple
        Contains the metrics produced by the strategy.

    """
    if ncpu > 1:
        price_sampler_data = list(price_sampler)
        args = [
            (pool, params, price_sampler_data, logging_queue)
            for pool, params in param_sampler
        ]

        listener = QueueListener(logging_queue, *logger.handlers)
        listener.start()
        with cpu_pool(ncpu) as clust:
            results = zip(*clust.starmap(strategy, args))
            clust.close()
            clust.join()  # coverage needs this
        listener.stop()

    else:
        results = []
        for pool, params in param_sampler:
            metrics = strategy(
                pool, params, price_sampler.restart(), logging_queue=logging_queue
            )
            results.append(metrics)
        results = tuple(zip(*results))

    return results


class SimPool(ABC):
    """
    The interface that must be implemented by pools used in simulations.

    See curvesim.pool.sim_interface for implementations.
    """

    def prepare_for_trades(self, timestamp):
        """
        Does any necessary preparation before computing and doing trades.

        The input timestamp can be used to fetch any auxiliary data
        needed to prep the state.

        Base implementation is a no-op.

        Parameters
        ----------
        timestamp : datetime.datetime
            the time to sample from
        """
        pass

    @abstractmethod
    def price(self, coin_in, coin_out, use_fee=True):
        """
        Returns the spot price of `coin_in` quoted in terms of `coin_out`,
        i.e. the ratio of output coin amount to input coin amount for
        an "infinitesimally" small trade.

        Coin IDs should be strings but as a legacy feature integer indices
        corresponding to the pool implementation are allowed (caveat lector).

        The indices are assumed to include base pool underlyer indices.

        Parameters
        ----------
        coin_in : str, int
            ID of coin to be priced; in a swapping context, this is
            the "in"-token.
        coin_out : str, int
            ID of quote currency; in a swapping context, this is the
            "out"-token.
        use_fee: bool, default=False
            Deduct fees.

        Returns
        -------
        float
            Price of `coin_in` quoted in `coin_out`
        """
        raise NotImplementedError

    @abstractmethod
    def trade(self, coin_in, coin_out, size):
        """
        Perform an exchange between two coins.

        Coin IDs should be strings but as a legacy feature integer indices
        corresponding to the pool implementation are allowed (caveat lector).

        Parameters
        ----------
        coin_in : str, int
            ID of "in" coin.
        coin_out : str, int
            ID of "out" coin.
        size : int
            Amount of coin `i` being exchanged.

        Returns
        -------
        (int, int, int)
            (amount of coin `j` received, trading fee, volume)

            Note that coin amounts and fee are in native token units but `volume`
            is normalized to be in the same units as pool value.  This enables
            cross-token comparisons and totaling of volume.
        """
        raise NotImplementedError

    @abstractmethod
    def get_price_depth(self):
        """
        Returns the price depth between pairs of coins in the pool.
        """
        raise NotImplementedError

    @abstractmethod
    def make_error_fns(self):
        """
        Returns the pricing error functions needed for determining the
        optimal arbitrage in simulations.
        """
        raise NotImplementedError
