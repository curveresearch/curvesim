from abc import ABC, abstractmethod
from multiprocessing import Pool as cpu_pool


def run_pipeline(param_sampler, price_sampler, strategy, ncpu=4):
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
        args = [(pool, params, price_sampler_data) for pool, params in param_sampler]

        with cpu_pool(ncpu) as clust:
            results = zip(*clust.starmap(strategy, args))

    else:
        results = []
        for pool, params in param_sampler:
            metrics = strategy(pool, params, price_sampler.restart())
            results.append(metrics)
        results = tuple(zip(*results))

    return results


class SimPool(ABC):
    """
    A template class for creating simulation interfaces for pools.
    See pool.stablewap.interfaces.StableSwapSimPool

    This component is likely to change.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._coin_indices = None

    @property
    def coin_indices(self):
        if self._coin_indices:
            indices = self._coin_indices
        else:
            # pylint: disable-next=no-member
            indices = self._init_coin_indices(self.metadata)
            self._coin_indices = indices
        return indices

    @staticmethod
    @abstractmethod
    def _init_coin_indices(metadata):
        raise NotImplementedError

    @abstractmethod
    def price(self, coin_in, coin_out, use_fee=True):
        raise NotImplementedError

    @abstractmethod
    def trade(self, coin_in, coin_out, size):
        raise NotImplementedError

    @abstractmethod
    def test_trade(self, coin_in, coin_out, dx, state=None):
        raise NotImplementedError

    @abstractmethod
    def make_error_fns(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def pricing_fns(self):
        raise NotImplementedError

    @abstractmethod
    def get_pool_state(self):
        raise NotImplementedError

    def get_coin_indices(self, *coins):
        """
        Gets the pool indices for the input coin names.
        Uses the coin_indices set by _init_coin_indices.
        """
        coin_indices = self.coin_indices
        return [self._get_coin_index(coin_indices, c) for c in coins]

    @staticmethod
    def _get_coin_index(coin_indices, coin_id):
        """
        Gets the index for a single coin based on its name.
        Uses the coin_indices set by _init_coin_indices.
        """
        if isinstance(coin_id, str):
            coin_id = coin_indices[coin_id]
        return coin_id
