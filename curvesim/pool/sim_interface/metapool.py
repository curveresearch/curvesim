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

    @override
    def price(self, coin_in, coin_out, use_fee=True):
        i, j = self.get_coin_indices(coin_in, coin_out)
        bp_token_index = self.n_total

        if bp_token_index not in (i, j):
            return self.dydx(i, j, use_fee=use_fee)

        if i == bp_token_index:
            i = self.max_coin

        if j == bp_token_index:
            j = self.max_coin

        if i == j:
            raise CurvesimValueError("Duplicate coin indices.")

        xp = self._xp()
        return self._dydx(i, j, xp=xp, use_fee=use_fee)

    @override
    def trade(self, coin_in, coin_out, amount_in):
        """
        Trade between two coins in a pool.
        Coins run over basepool underlyers.

        Note all quantities are in D units.
        """
        i, j = self.get_coin_indices(coin_in, coin_out)
        amount_out, fee = self.exchange_underlying(i, j, amount_in)
        return amount_out, fee

    def test_trade(self, coin_in, coin_out, factor, use_fee=True):
        """
        Trade between top-level coins but leaves balances affected.

        Used to compute liquidity density.
        """
        i, j = self.get_coin_indices(coin_in, coin_out)
        bp_token_index = self.n_total
        if bp_token_index not in (i, j):
            raise CurvesimValueError("Must be trade with basepool token.")

        max_coin = self.max_coin

        if i == bp_token_index:
            i = max_coin

        if j == bp_token_index:
            j = max_coin

        if i == j:
            raise CurvesimValueError("Duplicate coin indices.")

        dx = self.balances[i] // factor

        with self.use_snapshot_context():
            self.exchange(i, j, dx)

            xp_post = self._xp()
            price = self._dydx(i, j, xp_post, use_fee=use_fee)

        return price

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
        max_coin = self.max_coin
        symbols = self.coin_names[:max_coin] + self.basepool.coin_names
        addresses = self.coin_addresses[:max_coin] + self.basepool.coin_addresses

        return SimAssets(symbols, addresses, self.chain)
