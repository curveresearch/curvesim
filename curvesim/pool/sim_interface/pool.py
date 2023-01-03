from itertools import combinations

from numpy import isnan

from ..stableswap import CurvePool
from ..stableswap import functions as pool_functions
from .simpool import SimStableswapBase


class SimCurvePool(SimStableswapBase, CurvePool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def _precisions(self):
        return self.rates[:]

    def _init_coin_indices(self):
        return {name: i for i, name in enumerate(self.coin_names)}

    @property
    def _base_index_combos(self):
        base_idx = range(self.n)
        base_index_combos = combinations(base_idx, 2)
        return base_index_combos

    def price(self, coin_in, coin_out, use_fee=True):
        i, j = self.get_coin_indices(coin_in, coin_out)
        return self.dydx(i, j, use_fee=use_fee)

    def trade(self, coin_in, coin_out, size):
        i, j = self.get_coin_indices(coin_in, coin_out)

        out_amount, fee = self.exchange(i, j, size)
        # in D units
        volume = size * self._precisions[i] // 10**18

        return out_amount, fee, volume

    def _test_trade(self, coin_in, coin_out, factor):
        i, j = self.get_coin_indices(coin_in, coin_out)

        x = self.balances
        p = self.rates
        xp = self._xp_mem(x, p)
        size = xp[i] // factor

        exchange_args = (self.balances, self.rates, self.A, self.fee, self.admin_fee)

        output = pool_functions.exchange(
            i, j, size, *exchange_args, fee_mul=self.fee_mul
        )

        xp_post = [x * p // 10**18 for x, p in zip(output[0], self.rates)]

        dydx = pool_functions.dydx(
            i, j, xp_post, self.A, fee=self.fee, fee_mul=self.fee_mul
        )

        return (dydx,) + output

    def make_error_fns(self):
        # Note: for performance, does not support string coin-names

        args = [self.balances, self.rates, self.A, self.fee, self.admin_fee]
        xp = self._xp_mem(self.balances, self.rates)

        all_idx = range(self.n_total)
        index_combos = combinations(all_idx, 2)

        def get_trade_bounds(i, j):
            xp_j = int(xp[j] * 0.01)
            high = pool_functions.get_y(j, i, xp_j, xp, self.A) - xp[i]

            return (0, high)

        def post_trade_price_error(dx, i, j, price_target):
            dx = int(dx) * 10**18 // self.rates[i]

            if dx > 0:
                output = pool_functions.exchange(
                    i, j, dx, xp=xp, *args, fee_mul=self.fee_mul
                )

                xp_post = self._xp_mem(output[0], self.rates)
            else:
                xp_post = xp

            dydx = pool_functions.dydx(
                i, j, xp_post, self.A, fee=self.fee, fee_mul=self.fee_mul
            )

            return dydx - price_target

        def post_trade_price_error_multi(dxs, price_targets, coins):
            _args = args[:]
            _xp = xp

            # Do trades
            for k, pair in enumerate(coins):
                i, j = pair

                if isnan(dxs[k]):
                    dx = 0
                else:
                    dx = int(dxs[k]) * 10**18 // self.rates[i]

                if dx > 0:
                    output = pool_functions.exchange(
                        i, j, dx, *_args, fee_mul=self.fee_mul, xp=_xp
                    )

                    _args[0] = output[0]  # update x
                    _xp = self._xp_mem(_args[0], self.rates)

            # Record price errors
            errors = []
            for k, pair in enumerate(coins):
                dydx = pool_functions.dydx(
                    *pair, _xp, self.A, fee=self.fee, fee_mul=self.fee_mul
                )
                errors.append(dydx - price_targets[k])

            return errors

        return (
            get_trade_bounds,
            post_trade_price_error,
            post_trade_price_error_multi,
            index_combos,
        )
