from collections import namedtuple

from numpy import isnan

from curvesim.pool.stableswap.metapool import CurveMetaPool

from .. import functions as pool_functions

# Namedtuples for pool states
PoolState = namedtuple(
    "PoolState", ["x", "p", "A", "fee", "fee_mul", "tokens", "admin_fee"]
)


def _get_pool_state(pool):
    if isinstance(pool, CurveMetaPool):
        p = pool.rate_multiplier
    else:
        p = pool.rates[:]
    return PoolState(
        pool.balances[:], p, pool.A, pool.fee, pool.fee_mul, pool.tokens, pool.admin_fee
    )


def _precisions(self):
    state = self.get_pool_state()
    return state.p


def _init_pool_coin_indices(metadata):
    coin_names = metadata["coins"]["names"]
    coin_indices = range(len(coin_names))
    return dict(zip(coin_names, coin_indices))


def _price(self, coin_in, coin_out, use_fee=True):
    i, j = self.get_coin_indices(coin_in, coin_out)
    assert i != j
    return self.pool.dydx(i, j, use_fee=use_fee)


def _trade(self, coin_in, coin_out, size):
    i, j = self.get_coin_indices(coin_in, coin_out)
    assert i != j

    output = self.pool.exchange(i, j, size)
    self.set_pool_state()

    return output


def _test_trade(self, coin_in, coin_out, dx, state=None):
    i, j = self.get_coin_indices(coin_in, coin_out)
    assert i != j

    state = state or self.get_pool_state()
    exchange_args = (state.x, state.p, state.A, state.fee, state.admin_fee)

    output = pool_functions.exchange(i, j, dx, *exchange_args, fee_mul=state.fee_mul)

    xp_post = [x * p // 10**18 for x, p in zip(output[0], state.p)]

    dydx = pool_functions.dydx(
        i, j, xp_post, state.A, fee=state.fee, fee_mul=state.fee_mul
    )

    return (dydx,) + output


def _make_error_fns(self):
    # Note: for performance, does not support string coin-names

    state = self.get_pool_state()
    args = [state.x, state.p, state.A, state.fee, state.admin_fee]
    xp = pool_functions.get_xp(state.x, state.p)

    def get_trade_bounds(i, j):
        xp_j = int(xp[j] * 0.01)
        high = pool_functions.get_y(j, i, xp_j, xp, state.A) - xp[i]

        return (0, high)

    def post_trade_price_error(dx, i, j, price_target):
        dx = int(dx) * 10**18 // state.p[i]

        if dx > 0:
            output = pool_functions.exchange(
                i, j, dx, xp=xp, *args, fee_mul=state.fee_mul
            )

            xp_post = pool_functions.get_xp(output[0], state.p)
        else:
            xp_post = xp

        dydx = pool_functions.dydx(
            i, j, xp_post, state.A, fee=state.fee, fee_mul=state.fee_mul
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
                dx = int(dxs[k]) * 10**18 // state.p[i]

            if dx > 0:
                output = pool_functions.exchange(
                    i, j, dx, *_args, fee_mul=state.fee_mul, xp=_xp
                )

                _args[0] = output[0]  # update x
                _xp = pool_functions.get_xp(_args[0], state.p)

        # Record price errors
        errors = []
        for k, pair in enumerate(coins):
            dydx = pool_functions.dydx(
                *pair, _xp, state.A, fee=state.fee, fee_mul=state.fee_mul
            )
            errors.append(dydx - price_targets[k])

        return errors

    return get_trade_bounds, post_trade_price_error, post_trade_price_error_multi


stableswap_pool_fns = (
    _price,
    _trade,
    _test_trade,
    _make_error_fns,
    _precisions,
    _get_pool_state,
    _init_pool_coin_indices,
)
