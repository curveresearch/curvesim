from itertools import combinations

from numpy import isnan

from curvesim.utils import override

from ..stableswap import CurvePool
from .simpool import SimStableswapBase


class SimCurvePool(SimStableswapBase, CurvePool):
    @property
    def _precisions(self):
        return self.rates[:]

    @override
    def _init_coin_indices(self):
        return {name: i for i, name in enumerate(self.coin_names)}

    @override
    def price(self, coin_in, coin_out, use_fee=True):
        i, j = self.get_coin_indices(coin_in, coin_out)
        return self.dydx(i, j, use_fee=use_fee)

    @override
    def trade(self, coin_in, coin_out, size):
        i, j = self.get_coin_indices(coin_in, coin_out)

        out_amount, fee = self.exchange(i, j, size)
        # in D units
        volume = size * self._precisions[i] // 10**18

        return out_amount, fee, volume

    @override
    def test_trade(self, coin_in, coin_out, factor, use_fee=True):
        """
        This does the trade but leaves balances unaffected.

        Used to compute liquidity density.
        """
        i, j = self.get_coin_indices(coin_in, coin_out)

        size = self.balances[i] // factor

        with self.use_snapshot_context():
            self.exchange(i, j, size)
            price = self.dydx(i, j, use_fee=use_fee)

        return price

    @override
    def make_error_fns(self):
        # Note: for performance, does not support string coin-names

        xp = self._xp_mem(self.balances, self.rates)

        all_idx = range(self.n_total)
        index_combos = combinations(all_idx, 2)

        def get_trade_bounds(i, j):
            xp_j = int(xp[j] * 0.01)
            high = self.get_y(j, i, xp_j, xp) - xp[i]
            return (0, high)

        def post_trade_price_error(dx, i, j, price_target):
            dx = int(dx) * 10**18 // self.rates[i]

            with self.use_snapshot_context():
                if dx > 0:
                    self.exchange(i, j, dx)

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
                        dx = int(dxs[k]) * 10**18 // self.rates[i]

                    if dx > 0:
                        self.exchange(i, j, dx)

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
