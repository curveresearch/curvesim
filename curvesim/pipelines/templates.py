from multiprocessing import Pool as cpu_pool
from types import MethodType


def run_pipeline(param_sampler, price_sampler, strategy, ncpu=4):
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
    def _set_pool_interface(self, pool, pool_function_dict):
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
        return self._get_pool_state(self.pool)

    def set_pool_state(self):
        self.pool_state = self.get_pool_state()

    def get_coin_indices(self, *coins):
        coin_indices = self.coin_indices
        return [self._get_coin_index(coin_indices, c) for c in coins]

    @staticmethod
    def _get_coin_index(coin_indices, coin_id):
        if isinstance(coin_id, str):
            coin_id = coin_indices[coin_id]
        return coin_id
