from collections import namedtuple
from itertools import combinations

from gmpy2 import mpz
from numpy import isnan

from curvesim.pipelines.templates import SimInterface

from . import functions as pool_functions
from .metapool import CurveMetaPool
from .pool import CurvePool
from .raipool import CurveRaiPool


class StableSwapSimInterface(SimInterface):
    def __init__(self, pool):
        pool_function_dict = stableswap_interface_fns[type(pool)]
        self._set_pool_interface(pool, pool_function_dict)

        self.pricing_fns = stableswap_pricing_fns[type(pool)]
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
        p = getattr(state, "p_base", state.p)

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


# Namedtuples for pool states
PoolState = namedtuple(
    "PoolState", ["x", "p", "A", "fee", "fee_mul", "tokens", "admin_fee"]
)


MetaPoolState = namedtuple(
    "MetaPoolState",
    [
        "x",
        "x_base",
        "p",
        "p_base",
        "A",
        "A_base",
        "fee",
        "fee_base",
        "fee_mul",
        "fee_mul_base",
        "tokens",
        "tokens_base",
        "admin_fee",
        "rates",
    ],
)


# Functions for stableswap.CurvePool
def _get_pool_state(p):
    return PoolState(p.x[:], p.p[:], p.A, p.fee, p.fee_mul, p.tokens, p.admin_fee)


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


# Functions for stableswap.CurveMetaPool
def _get_metapool_state(pool):
    state_pairs = zip(_get_pool_state(pool), _get_pool_state(pool.basepool))

    args = [arg for pair in state_pairs for arg in pair]
    args[-1] = pool.rates()
    args = args

    return MetaPoolState(*args)


def _precisions_metapool(self):
    state = self.get_pool_state()
    return state.p[0 : self.max_coin] + state.p_base


def _init_metapool_coin_indices(metadata):
    meta_coin_names = metadata["coins"]["names"][:-1]
    base_coin_names = metadata["basepool"]["coins"]["names"]

    coin_names = meta_coin_names + base_coin_names
    coin_indices = range(len(coin_names))
    coin_dict = dict(zip(coin_names, coin_indices))

    bp_token_name = metadata["coins"]["names"][-1]
    bp_token_dict = dict.fromkeys([bp_token_name, "bp_token"], "bp_token")
    coin_dict.update(bp_token_dict)

    return coin_dict


def _metapool_price(self, coin_in, coin_out, use_fee=True):
    i, j = self.get_coin_indices(coin_in, coin_out)

    # Basepool LP token not used
    if i != "bp_token" and j != "bp_token":
        assert i != j
        return self.pool.dydx(i, j, use_fee=use_fee)

    # Basepool LP token used
    else:
        if i == "bp_token":
            i = self.max_coin

        if j == "bp_token":
            j = self.max_coin

        assert i != j
        xp = self.pool._xp()
        return self.pool._dydx(i, j, xp=xp, use_fee=use_fee)


def _metapool_trade(self, i, j, size):
    pool = self.pool
    trade_fn = pool.exchange_underlying

    if isinstance(i, str):
        i = self.coin_indices[i]
        if i == "bp_token":
            i = self.max_coin
            trade_fn = pool.exchange

    if isinstance(j, str):
        j = self.coin_indices[j]
        if j == "bp_token":
            j = self.max_coin
            trade_fn = pool.exchange

    assert i != j
    output = trade_fn(i, j, size)
    self.set_pool_state()

    return output


def _metapool_test_trade(self, coin_in, coin_out, dx, state=None):
    i, j = self.get_coin_indices(coin_in, coin_out)
    state = state or self.get_pool_state()
    max_coin = self.max_coin
    get_dydx, _get_dydx = self.pricing_fns

    # Basepool LP token not used in trade
    if i != "bp_token" and j != "bp_token":
        assert i != j
        return _test_trade_underlying(state, get_dydx, i, j, dx, max_coin)

    # Basepool LP token used in trade
    else:
        if i == "bp_token":
            i = max_coin

        if j == "bp_token":
            j = max_coin

        assert i != j
        return _test_trade_meta(state, _get_dydx, i, j, dx)


def _test_trade_underlying(state, pricing_fn, i, j, dx, max_coin):
    args = [
        state.x,
        state.x_base,
        state.rates,
        state.p_base,
        state.A,
        state.A_base,
        max_coin,
        state.tokens_base,
        state.fee,
        state.fee_base,
    ]

    output = pool_functions.exchange_underlying(
        i, j, dx, *args, admin_fee=state.admin_fee
    )

    # Update x values
    args[0:2] = output[0:2]

    # Update rates and tokens if needed
    if i < max_coin or j < max_coin:
        tokens_base = output[2]
        xp_base = pool_functions.get_xp(output[1], state.p_base)
        vp_base = pool_functions.get_virtual_price(xp_base, state.A_base, tokens_base)

        rates = state.rates[:]
        rates[max_coin] = vp_base

        args[2] = rates
        args[7] = tokens_base

    dydx = pricing_fn(i, j, *args)

    return (dydx,) + output


def _test_trade_meta(state, pricing_fn, i, j, dx):
    xp = pool_functions.get_xp(state.x, state.rates)
    exchange_args = (
        state.x,
        state.p,
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
        i, j, xp_post, state.A, p=state.p, fee=state.fee, fee_mul=state.fee_mul
    )

    return (dydx,) + output


def _make_metapool_error_fns(self):  # noqa: C901
    # Note: for performance, does not support string coin-names

    state = self.get_pool_state()
    get_dydx = self.pricing_fns[0]
    max_coin = self.max_coin
    args = [
        state.x,
        state.x_base,
        state.rates,
        state.p_base,
        state.A,
        state.A_base,
        max_coin,
        state.tokens_base,
        state.fee,
        state.fee_base,
    ]

    p_all = state.p[0:max_coin] + state.p_base
    xp_meta = pool_functions.get_xp(state.x, state.rates)
    xp_base = pool_functions.get_xp(state.x_base, state.p_base)

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
            high = pool_functions.get_y(meta_j, meta_i, xp_j, xp_meta, state.A)
            high -= xp_meta[meta_i]
            # high = high * 10**18 // state.rates[meta_i]
        else:
            xp_j = int(xp_base[base_j] * 0.01)
            high = pool_functions.get_y(base_j, base_i, xp_j, xp_base, state.A_base)
            high -= xp_base[base_i]
            # high = high * 10**18 // state.p_base[base_i]

        return (0, high)

    def post_trade_price_error(dx, i, j, price_target):
        _args = args[:]

        dx = int(dx) * 10**18 // p_all[i]

        if dx > 0:
            output = pool_functions.exchange_underlying(
                i, j, dx, *_args, admin_fee=state.admin_fee, base_xp=xp_base
            )

            # Update x, x_base, rates and tokens
            tokens_base = output[2]
            xp_base_post = [x * p // 10**18 for x, p in zip(output[1], state.p_base)]
            vp_base = pool_functions.get_virtual_price(
                xp_base_post, state.A_base, tokens_base
            )

            rates = state.rates[:]
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
                    i, j, dx, *_args, admin_fee=state.admin_fee, base_xp=_xp_base
                )

                # Update x, x_base, rates and tokens
                tokens_base = output[2]
                _xp_base = [x * p // 10**18 for x, p in zip(output[1], state.p_base)]
                vp_base = pool_functions.get_virtual_price(
                    _xp_base, state.A_base, tokens_base
                )

                rates = state.rates[:]
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

    return get_trade_bounds, post_trade_price_error, post_trade_price_error_multi


# Functions to set for each pool types
interface_functions = (
    "price",
    "trade",
    "test_trade",
    "make_error_fns",
    "precisions",
    "_get_pool_state",  # required
    "_init_coin_indices",  # required
)

stableswap_pool_fns = (
    _price,
    _trade,
    _test_trade,
    _make_error_fns,
    _precisions,
    _get_pool_state,
    _init_pool_coin_indices,
)

stableswap_metapool_fns = (
    _metapool_price,
    _metapool_trade,
    _metapool_test_trade,
    _make_metapool_error_fns,
    _precisions_metapool,
    _get_metapool_state,
    _init_metapool_coin_indices,
)

stableswap_pool_fns = dict(zip(interface_functions, stableswap_pool_fns))
stableswap_metapool_fns = dict(zip(interface_functions, stableswap_metapool_fns))
stableswap_interface_fns = {
    CurvePool: stableswap_pool_fns,
    CurveMetaPool: stableswap_metapool_fns,
    CurveRaiPool: stableswap_metapool_fns,
}

stableswap_pricing_fns = {
    CurvePool: (pool_functions.dydx, pool_functions.dydx),
    CurveMetaPool: (pool_functions.dydx_metapool, pool_functions.dydx),
    CurveRaiPool: (pool_functions.dydx_metapool_rai, pool_functions.dydx_rai),
}
