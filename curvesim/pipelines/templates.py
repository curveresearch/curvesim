from multiprocessing import Pool as cpu_pool
from types import MethodType


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
        price_sampler_data = [d for d in price_sampler]
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


class SimInterface:
    """
    A template class for creating simulation interfaces for pools.
    See pool.stablewap.interfaces.StableSwapSimInterface

    This component is likely to change.
    """

    def _set_pool_interface(self, pool, pool_function_dict):
        """
        Binds the pool and functions used in simulation to the interface.

        Parameters
        ----------
        pool :
            A pool object.

        pool_function_dict : dict
            A dict with interface method names as keys, and functions as values.

            Note: Currently, _get_pool_state, and _init_coin_indices are required.

        """
        self.pool = pool
        pool_function_dict = pool_function_dict.copy()

        # Set Required Functions
        self._get_pool_state = pool_function_dict.pop("_get_pool_state")
        self._init_coin_indices = pool_function_dict.pop("_init_coin_indices")

        # Set Additional Functions
        for interface_fn, pool_fn in pool_function_dict.items():
            bound_method = MethodType(pool_fn, self)
            setattr(self, interface_fn, bound_method)

        self.coin_indices = self._init_coin_indices(self.pool.metadata)
        self.set_pool_state()

    def get_pool_state(self):
        """
        Gets pool state using the provided _get_pool_state method
        """
        return self._get_pool_state(self.pool)

    def set_pool_state(self):
        """
        Records the current pool state in the interface's pool_state atttribute.
        """
        self.pool_state = self.get_pool_state()

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
