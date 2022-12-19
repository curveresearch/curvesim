from itertools import combinations

from curvesim.pipelines.templates import SimPool

from .. import functions as pool_functions
from . import registry


class StableSwapSimPool(SimPool):
    def __init__(self, pool):
        super().__init__()

        pool_function_dict = registry.get_stableswap_interface_functions(type(pool))
        self._set_pool_interface(pool, pool_function_dict)

        self.pricing_fns = registry.get_stableswap_pricing_functions(type(pool))
        self.next_timestamp = self.pool.next_timestamp

        all_idx = range(pool.n_total)
        base_idx = list(range(pool.n))
        self.max_coin = getattr(pool, "max_coin", None)

        if self.max_coin:
            base_idx[self.max_coin] = "bp_token"

        self.index_combos = list(combinations(all_idx, 2))
        self.base_index_combos = list(combinations(base_idx, 2))

    def get_liquidity_density(self, coin_in, coin_out, factor=10**8):
        # Fix: won't work for trades between meta-pool and basepool
        i, j = self.get_coin_indices(coin_in, coin_out)
        state = self.get_pool_state()

        x = getattr(state, "x_base", state.x)
        if hasattr(state, "p_base"):
            p = state.p_base
        else:
            p = state.p

        if i == "bp_token":
            i = self.max_coin
            x = state.x
            p = state.rates

        if j == "bp_token":
            j = self.max_coin
            x = state.x
            p = state.rates

        xp = pool_functions.get_xp(x, p)

        price_pre = self.price(coin_in, coin_out)
        output = self.test_trade(coin_in, coin_out, xp[i] // factor, state=state)
        price_post = output[0]
        LD1 = price_pre / ((price_pre - price_post) * factor)

        price_pre = self.price(coin_out, coin_in)
        output = self.test_trade(coin_out, coin_in, xp[j] // factor, state=state)
        price_post = output[0]
        LD2 = price_pre / ((price_pre - price_post) * factor)

        return (LD1 + LD2) / 2
