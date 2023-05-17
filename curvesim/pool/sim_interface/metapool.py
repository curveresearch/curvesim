from itertools import combinations

from numpy import isnan

from curvesim.exceptions import CurvesimValueError
from curvesim.pool.sim_interface.simpool import SimStableswapBase
from curvesim.pool.stableswap.metapool import CurveMetaPool
from curvesim.utils import override


class SimCurveMetaPool(SimStableswapBase, CurveMetaPool):
    @property
    def _precisions(self):
        p_base = self.basepool.rates[:]
        return [self.rate_multiplier, *p_base]

    @override
    def _init_coin_indices(self):
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
    def trade(self, coin_in, coin_out, size):
        """
        Trade between two coins in a pool.
        Coin index runs over basepool underlyers.
        We count only volume when one coin is the primary stable.
        """
        i, j = self.get_coin_indices(coin_in, coin_out)

        out_amount, fee = self.exchange_underlying(i, j, size)

        max_coin = self.max_coin
        if i < max_coin or j < max_coin:
            volume = size * self._precisions[i] // 10**18  # in D units
        else:
            volume = 0

        return out_amount, fee, volume

    @override
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

    @override
    def make_error_fns(self):  # noqa: C901
        # Note: for performance, does not support string coin-names

        max_coin = self.max_coin

        p_all = [self.rate_multiplier] + self.basepool.rates
        xp_meta = self._xp_mem(self.balances, self.rates)
        xp_base = self._xp_mem(self.basepool.balances, self.basepool.rates)

        all_idx = range(self.n_total)
        index_combos = combinations(all_idx, 2)

        def get_trade_bounds(i, j):
            base_i = i - max_coin
            base_j = j - max_coin
            meta_i = max_coin
            meta_j = max_coin
            if base_i < 0:
                meta_i = i
            if base_j < 0:
                meta_j = j

            if base_i < 0 or base_j < 0:
                xp_j = int(xp_meta[meta_j] * 0.01)
                high = self.get_y(meta_j, meta_i, xp_j, xp_meta)
                high -= xp_meta[meta_i]
            else:
                xp_j = int(xp_base[base_j] * 0.01)
                high = self.basepool.get_y(base_j, base_i, xp_j, xp_base)
                high -= xp_base[base_i]

            return (0, high)

        def post_trade_price_error(dx, i, j, price_target):
            dx = int(dx) * 10**18 // p_all[i]

            with self.use_snapshot_context():
                if dx > 0:
                    self.exchange_underlying(i, j, dx)

                dydx = self.dydxfee(i, j)

            return dydx - price_target

        def post_trade_price_error_multi(dxs, price_targets, coins):
            with self.use_snapshot_context():
                # Do trades
                for k, pair in enumerate(coins):
                    i, j = pair

                    if isnan(dxs[k]):
                        dx = 0
                    else:
                        dx = int(dxs[k]) * 10**18 // p_all[i]

                    if dx > 0:
                        self.exchange_underlying(i, j, dx)

                # Record price errors
                errors = []
                for k, pair in enumerate(coins):
                    i, j = pair
                    dydx = self.dydxfee(i, j)
                    errors.append(dydx - price_targets[k])

            return errors

        return (
            get_trade_bounds,
            post_trade_price_error,
            post_trade_price_error_multi,
            index_combos,
        )
