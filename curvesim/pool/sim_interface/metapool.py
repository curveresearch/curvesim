from itertools import combinations

from gmpy2 import mpz
from numpy import isnan

from curvesim.exceptions import CurvesimValueError
from curvesim.pool.sim_interface.simpool import SimStableswapBase
from curvesim.pool.stableswap.metapool import CurveMetaPool

from ..stableswap import functions as pool_functions


class SimCurveMetaPool(SimStableswapBase, CurveMetaPool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metadata = None  # set later by factory

    @property
    def _precisions(self):
        p_base = self.basepool.rates[:]
        return [self.rate_multiplier, *p_base]

    def _init_coin_indices(self):
        metadata = self.metadata
        meta_coin_names = metadata["coins"]["names"][:-1]
        base_coin_names = metadata["basepool"]["coins"]["names"]

        coin_names = meta_coin_names + base_coin_names
        coin_dict = {name: i for i, name in enumerate(coin_names)}

        bp_token_name = metadata["coins"]["names"][-1]
        bp_token_dict = dict.fromkeys([bp_token_name, "bp_token"], "bp_token")
        coin_dict.update(bp_token_dict)

        return coin_dict

    @property
    def _base_index_combos(self):
        base_idx = list(range(self.n))
        base_idx[self.max_coin] = "bp_token"
        base_index_combos = list(combinations(base_idx, 2))
        return base_index_combos

    def price(self, coin_in, coin_out, use_fee=True):
        i, j = self.get_coin_indices(coin_in, coin_out)

        # Basepool LP token not used
        if i != "bp_token" and j != "bp_token":
            return self.dydx(i, j, use_fee=use_fee)

        # Basepool LP token used
        else:
            if i == "bp_token":
                i = self.max_coin

            if j == "bp_token":
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
        if "bp_token" not in (i, j):
            raise CurvesimValueError("Must be trade with basepool token.")

        x = self.balances
        p = self.rates
        xp = pool_functions.get_xp(x, p)

        max_coin = self.max_coin
        _get_dydx = pool_functions.dydx

        if i == "bp_token":
            i = max_coin

        if j == "bp_token":
            j = max_coin

        if i == j:
            raise CurvesimValueError("Duplicate coin indices.")

        size = xp[i] // factor
        return _test_trade_meta(self, _get_dydx, i, j, size)

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
        xp_meta = pool_functions.get_xp(self.balances, self.rates)
        xp_base = pool_functions.get_xp(self.basepool.balances, self.basepool.rates)

        all_idx = range(self.n_total)
        index_combos = list(combinations(all_idx, 2))

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
                high = pool_functions.get_y(meta_j, meta_i, xp_j, xp_meta, self.A)
                high -= xp_meta[meta_i]
                # high = high * 10**18 // self.rates[meta_i]
            else:
                xp_j = int(xp_base[base_j] * 0.01)
                high = pool_functions.get_y(
                    base_j, base_i, xp_j, xp_base, self.basepool.A
                )
                high -= xp_base[base_i]
                # high = high * 10**18 // self.p_base[base_i]

            return (0, high)

        def post_trade_price_error(dx, i, j, price_target):
            _args = args[:]

            dx = int(dx) * 10**18 // p_all[i]

            if dx > 0:
                output = pool_functions.exchange_underlying(
                    i, j, dx, *_args, admin_fee=self.admin_fee, base_xp=xp_base
                )

                # Update x, x_base, rates and tokens
                tokens_base = output[2]
                xp_base_post = [
                    x * p // 10**18 for x, p in zip(output[1], self.basepool.rates)
                ]
                vp_base = pool_functions.get_virtual_price(
                    xp_base_post, self.basepool.A, tokens_base
                )

                rates = self.rates[:]
                rates[max_coin] = vp_base

                _args[0:3] = output[0:2] + (rates,)
                _args[7] = tokens_base

            else:
                xp_base_post = xp_base

            dydx = get_dydx(i, j, *_args, base_xp=xp_base_post)

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


def _test_trade_meta(state, pricing_fn, i, j, dx):
    xp = pool_functions.get_xp(state.balances, state.rates)
    exchange_args = (
        state.balances,
        state.rates,
        state.A,
        state.fee,
        state.admin_fee,
        xp,
        state.fee_mul,
    )

    output = pool_functions.exchange(
        i,
        j,
        dx,
        *exchange_args,
    )

    xp_post = pool_functions.get_xp(output[0], state.rates)

    dydx = pricing_fn(
        i, j, xp_post, state.A, p=state.rates, fee=state.fee, fee_mul=state.fee_mul
    )

    return (dydx,) + output
