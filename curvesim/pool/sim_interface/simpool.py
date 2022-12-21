from abc import ABC, abstractmethod
from itertools import combinations

from curvesim.pipelines.templates import SimPool

from ..stableswap import functions as pool_functions


class SimStableswapBase(SimPool, ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._coin_indices = None

    @abstractmethod
    def _init_coin_indices(self):
        """Produces the coin ID to index mapping from the pool's metadata."""
        raise NotImplementedError

    @property
    def coin_indices(self):
        """Return dict mapping coin ID to index."""
        if self._coin_indices:
            indices = self._coin_indices
        else:
            indices = self._init_coin_indices()
            self._coin_indices = indices
        return indices

    def get_coin_indices(self, *coins_ids):
        """
        Gets the pool indices for the input coin names.
        Uses the coin_indices set by _init_coin_indices.
        """
        coin_indices = []
        for coin_id in coins_ids:
            if isinstance(coin_id, str):
                coin_id = self.coin_indices[coin_id]
            coin_indices.append(coin_id)

        return coin_indices

    def get_liquidity_density(self, coin_in, coin_out, factor=10**8):
        """
        Only for top-level liquidity density.  Cannot compare between
        coins in basepool and primary stablecoin in metapool.
        """
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

    def get_price_depth(self):
        base_idx = list(range(self.n))

        if hasattr(self, "max_coin"):
            # pylint: disable-next=E0203,E1126
            base_idx[self.max_coin] = "bp_token"

        base_index_combos = list(combinations(base_idx, 2))

        LD = []
        for i, j in base_index_combos:
            ld = self.get_liquidity_density(i, j)
            LD.append(ld)
        return LD
