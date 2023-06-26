from curvesim.exceptions import CurvesimValueError, SimPoolError
from curvesim.pipelines.templates import SimAssets
from curvesim.pipelines.templates.sim_pool import SimPool
from curvesim.utils import cache, override

from ..stableswap import CurveMetaPool
from .coin_indices import CoinIndicesMixin


class SimCurveMetaPool(SimPool, CoinIndicesMixin, CurveMetaPool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # The rates check has a couple special cases:
        # 1. For metapools, we need to use the basepool rates
        #    instead of the virtual price for the basepool.
        # 2. If `rate_multiplier` is passed as a kwarg, this will
        #    likely be some price, which we should skip.
        rates = [self.rate_multiplier] + self.basepool.rates
        if "rate_multiplier" in kwargs:
            rates = rates[1:]

        for r in rates:
            if r != 10**18:
                raise SimPoolError("SimPool must have 18 decimals for each coin.")

    @property
    @override
    @cache
    def coin_indices(self):
        """Return dict mapping coin ID to index."""

        meta_coin_names = self.coin_names[:-1]
        base_coin_names = self.basepool.coin_names
        bp_token_name = self.coin_names[-1]

        # indexing from primary stable, through basepool underlyers,
        # and then basepool LP token.
        coin_names = [*meta_coin_names, *base_coin_names, bp_token_name]
        coin_dict = {name: i for i, name in enumerate(coin_names)}

        return coin_dict

    @property
    @override
    def coin_balances(self):
        """Return dict mapping coin ID to coin balances."""
        meta_balances = self.balances[:-1]
        base_balances = self.basepool.balances
        bp_token_balances = self.balances[-1]

        balances = [*meta_balances, *base_balances, bp_token_balances]

        return dict(zip(self.coin_indices, balances))

    @override
    def price(self, coin_in, coin_out, use_fee=True):
        i, j = self.get_coin_indices(coin_in, coin_out)
        bp_token_index = self.n_total

        if bp_token_index not in (i, j):
            return self.dydx(i, j, use_fee=use_fee)

        i, j = self.get_meta_coin_indices(i, j, bp_token_index)
        xp = self._xp()
        return self._dydx(i, j, xp=xp, use_fee=use_fee)

    @override
    def trade(self, coin_in, coin_out, amount_in):
        """
        Trade between two coins in a pool.

        Note all quantities are in D units.
        """
        i, j = self.get_coin_indices(coin_in, coin_out)
        bp_token_index = self.n_total

        if bp_token_index not in (i, j):
            return self.exchange_underlying(i, j, amount_in)

        i, j = self.get_meta_coin_indices(i, j, bp_token_index)
        return self.exchange(i, j, amount_in)

    def get_meta_coin_indices(self, i, j, bp_token_index):
        """
        Get metapool coin indices from the output of get_coin_indices.
        """
        max_coin = self.max_coin

        if i == bp_token_index:
            i = max_coin

        if j == bp_token_index:
            j = max_coin

        if i == j:
            raise CurvesimValueError("Duplicate coin indices.")

        if i > max_coin or j > max_coin:
            raise CurvesimValueError(
                f"Index exceeds max metapool index (Input: {(i,j)}, Max: {max_coin})."
            )

        return i, j

    def get_in_amount(self, coin_in, coin_out, out_balance_perc):
        i, j = self.get_coin_indices(coin_in, coin_out)

        max_coin = self.max_coin

        xp_meta = self._xp_mem(self.balances, self.rates)
        xp_base = self._xp_mem(self.basepool.balances, self.basepool.rates)

        base_i = i - max_coin
        base_j = j - max_coin
        meta_i = max_coin
        meta_j = max_coin
        if base_i < 0:
            meta_i = i
        if base_j < 0:
            meta_j = j

        if base_i < 0 or base_j < 0:
            xp_j = int(xp_meta[meta_j] * out_balance_perc)
            in_amount = self.get_y(meta_j, meta_i, xp_j, xp_meta)
            in_amount -= xp_meta[meta_i]
        else:
            xp_j = int(xp_base[base_j] * out_balance_perc)
            in_amount = self.basepool.get_y(base_j, base_i, xp_j, xp_base)
            in_amount -= xp_base[base_i]

        return in_amount

    @property
    @override
    @cache
    def assets(self):
        symbols = self.coin_names[:-1] + self.basepool.coin_names
        addresses = self.coin_addresses[:-1] + self.basepool.coin_addresses

        return SimAssets(symbols, addresses, self.chain)
