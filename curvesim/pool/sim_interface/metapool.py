from itertools import combinations

from gmpy2 import mpz
from numpy import isnan

from curvesim.exceptions import CurvesimValueError
from curvesim.pool.sim_interface.simpool import SimStableswapBase
from curvesim.pool.snapshot import CurveMetaPoolBalanceSnapshot
from curvesim.pool.stableswap.metapool import CurveMetaPool

from ..stableswap import functions as pool_functions


class SimCurveMetaPool(SimStableswapBase, CurveMetaPool):

    snapshot_class = CurveMetaPoolBalanceSnapshot

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def _precisions(self):
        p_base = self.basepool.rates[:]
        return [self.rate_multiplier, *p_base]

    def _init_coin_indices(self):
        meta_coin_names = self.coin_names[:-1]
        base_coin_names = self.basepool.coin_names
        bp_token_name = self.coin_names[-1]

        # indexing from primary stable, through basepool underlyers,
        # and then basepool LP token.
        coin_names = [*meta_coin_names, *base_coin_names, bp_token_name]
        coin_dict = {name: i for i, name in enumerate(coin_names)}

        return coin_dict

    @property
    def _base_index_combos(self):
        """
        Our convention for the basepool LP token index is to use
        the total number of stablecoins (including basepool).
        This removes ambiguity as it is one "off the end" and thus
        either doesn't exist or is the basepool LP token.
        """
        base_idx = list(range(self.n))
        base_idx[self.max_coin] = self.n_total
        base_index_combos = combinations(base_idx, 2)
        return base_index_combos

    def price(self, coin_in, coin_out, use_fee=True):
        i, j = self.get_coin_indices(coin_in, coin_out)
        bp_token_index = self.n_total

        if bp_token_index not in (i, j):
            return self.dydx(i, j, use_fee=use_fee)
        else:
            if i == bp_token_index:
                i = self.max_coin

            if j == bp_token_index:
                j = self.max_coin

            if i == j:
                raise CurvesimValueError("Duplicate coin indices.")

            xp = self._xp()
            return self._dydx(i, j, xp=xp, use_fee=use_fee)

    def trade(self, i, j, size):
        """
        Trade between two coins in a pool.
        Coin index runs over basepool underlyers.
        We count only volume when one coin is the primary stable.
        """
        if i == j:
            raise CurvesimValueError("Duplicate coin indices.")

        out_amount, fee = self.exchange_underlying(i, j, size)

        max_coin = self.max_coin
        if i < max_coin or j < max_coin:
            volume = size * self._precisions[i] // 10**18  # in D units
        else:
            volume = 0

        return out_amount, fee, volume

    def _test_trade(
        self,
        coin_in,
        coin_out,
        factor,
    ):
        """
        Trade between top-level coins.
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

        xp = self._xp()
        dx = xp[i] // factor

        snapshot = self.get_snapshot()

        self.exchange(i, j, dx)

        xp_post = self._xp()
        dydx = self._dydx(i, j, xp_post, use_fee=True)

        self.revert_to_snapshot(snapshot)

        return (dydx,)

    def make_error_fns(self):  # noqa: C901
        # Note: for performance, does not support string coin-names

        get_dydx = pool_functions.dydx_metapool
        max_coin = self.max_coin
        args = [
            self.balances,
            self.basepool.balances,
            self.rates,
            self.basepool.rates,
            self.A,
            self.basepool.A,
            max_coin,
            self.basepool.tokens,
            self.fee,
            self.basepool.fee,
        ]

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

            snapshot = self.get_snapshot()
            if dx > 0:
                self.exchange_underlying(i, j, dx)

            dydx = self.dydxfee(i, j)
            self.revert_to_snapshot(snapshot)

            return dydx - price_target

        def post_trade_price_error_multi(dxs, price_targets, coins):
            _args = args[:]
            _xp_base = xp_base

            # Do trades
            for k, pair in enumerate(coins):
                i, j = pair

                if isnan(dxs[k]):
                    dx = 0
                else:
                    dx = int(dxs[k]) * 10**18 // p_all[i]

                if dx > 0:
                    output = pool_functions.exchange_underlying(
                        i, j, dx, *_args, admin_fee=self.admin_fee, base_xp=_xp_base
                    )

                    # Update x, x_base, rates and tokens
                    tokens_base = output[2]
                    _xp_base = [
                        x * p // 10**18
                        for x, p in zip(output[1], self.basepool.rates)
                    ]
                    vp_base = pool_functions.get_virtual_price(
                        _xp_base, self.basepool.A, tokens_base
                    )

                    rates = self.rates[:]
                    rates[max_coin] = vp_base

                    _args[0:3] = output[0:2] + (rates,)
                    _args[7] = tokens_base

            # Record price errors
            errors = []
            _xp_base = [mpz(x) for x in _xp_base]
            for k, pair in enumerate(coins):

                dydx = get_dydx(*pair, *_args, base_xp=_xp_base)
                errors.append(dydx - price_targets[k])

            return errors

        return (
            get_trade_bounds,
            post_trade_price_error,
            post_trade_price_error_multi,
            index_combos,
        )
