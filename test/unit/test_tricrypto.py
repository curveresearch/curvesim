"""
Unit tests for CurveCryptoPool for n = 3

Tests are against the tricrypto-ng contract.
"""
import os
from itertools import permutations

import boa
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from curvesim.pool import CurveCryptoPool
from curvesim.pool.cryptoswap.calcs import get_p, get_y, newton_D
from curvesim.pool.cryptoswap.calcs.tricrypto_ng import (
    MAX_A,
    MAX_GAMMA,
    MIN_A,
    MIN_GAMMA,
    PRECISION,
    _newton_y,
    wad_exp,
)


def get_math(tricrypto):
    _base_dir = os.path.dirname(__file__)
    filepath = os.path.join(_base_dir, "../fixtures/curve/tricrypto_math.vy")
    _math = tricrypto.MATH()
    MATH = boa.load_partial(filepath).at(_math)
    return MATH


def initialize_pool(vyper_tricrypto):
    """
    Initialize python-based pool from the state variables of the
    vyper-based implementation.
    """
    A = vyper_tricrypto.A()
    gamma = vyper_tricrypto.gamma()
    n_coins = 3
    precisions = vyper_tricrypto.precisions()
    mid_fee = vyper_tricrypto.mid_fee()
    out_fee = vyper_tricrypto.out_fee()
    fee_gamma = vyper_tricrypto.fee_gamma()

    admin_fee = vyper_tricrypto.ADMIN_FEE()

    allowed_extra_profit = vyper_tricrypto.allowed_extra_profit()
    adjustment_step = vyper_tricrypto.adjustment_step()
    ma_half_time = vyper_tricrypto.ma_time()

    price_scale = [vyper_tricrypto.price_scale(i) for i in range(n_coins - 1)]
    price_oracle = [vyper_tricrypto.price_oracle(i) for i in range(n_coins - 1)]
    last_prices = [vyper_tricrypto.last_prices(i) for i in range(n_coins - 1)]
    last_prices_timestamp = vyper_tricrypto.last_prices_timestamp()
    balances = [vyper_tricrypto.balances(i) for i in range(n_coins)]
    # Use the cached `D`. See warning for `virtual_price` below
    D = vyper_tricrypto.D()
    lp_total_supply = vyper_tricrypto.totalSupply()
    xcp_profit = vyper_tricrypto.xcp_profit()
    xcp_profit_a = vyper_tricrypto.xcp_profit_a()

    pool = CurveCryptoPool(
        A=A,
        gamma=gamma,
        n=n_coins,
        precisions=precisions,
        mid_fee=mid_fee,
        out_fee=out_fee,
        allowed_extra_profit=allowed_extra_profit,
        fee_gamma=fee_gamma,
        adjustment_step=adjustment_step,
        admin_fee=admin_fee,
        ma_half_time=ma_half_time,
        price_scale=price_scale,
        price_oracle=price_oracle,
        last_prices=last_prices,
        last_prices_timestamp=last_prices_timestamp,
        balances=balances,
        D=D,
        tokens=lp_total_supply,
        xcp_profit=xcp_profit,
        xcp_profit_a=xcp_profit_a,
    )

    assert pool.A == vyper_tricrypto.A()
    assert pool.gamma == vyper_tricrypto.gamma()
    assert pool.balances == balances
    assert pool.price_scale == price_scale
    assert pool._price_oracle == price_oracle  # pylint: disable=protected-access
    assert pool.last_prices == last_prices
    assert pool.last_prices_timestamp == last_prices_timestamp
    assert pool.D == vyper_tricrypto.D()
    assert pool.tokens == lp_total_supply
    assert pool.xcp_profit == xcp_profit
    assert pool.xcp_profit_a == xcp_profit_a

    # WARNING: both `virtual_price` and `D` are cached values
    # so depending on the test, may not be updated to be
    # consistent with the rest of the pool state.
    #
    # Allowing this simplifies testing since we can avoid
    # coupling tests of basic functionality with the tests
    # for the complex newton calculations.
    #
    # We think it makes sense the initialized pool should
    # at least match the vyper pool (inconsistencies and all).
    # When full consistency is required, the `update_cached_values`
    # helper function should be utilized before calling
    # `initialize_pool`.
    virtual_price = vyper_tricrypto.virtual_price()
    pool.virtual_price = virtual_price

    return pool


def get_real_balances(virtual_balances, precisions, price_scale):
    """
    Convert from units of D to native token units using the
    given price scale.
    """
    assert len(virtual_balances) == 3
    balances = [x // p for x, p in zip(virtual_balances, precisions)]
    balances[1] = balances[1] * PRECISION // price_scale[0]
    balances[2] = balances[2] * PRECISION // price_scale[1]
    return balances


def update_cached_values(vyper_tricrypto):
    """
    Useful test helper after we manipulate the pool state.

    Calculates `D` and `virtual_price` from pool state and caches
    them in the appropriate storage.
    """
    A = vyper_tricrypto.A()
    gamma = vyper_tricrypto.gamma()
    xp = vyper_tricrypto.eval("self.xp()")
    xp = list(xp)  # boa doesn't like its own tuple wrapper
    MATH = get_math(vyper_tricrypto)
    D = MATH.newton_D(A, gamma, xp)  # pylint: disable=no-member
    vyper_tricrypto.eval(f"self.D={D}")
    total_supply = vyper_tricrypto.totalSupply()
    vyper_tricrypto.eval(
        f"self.virtual_price=10**18 * self.get_xcp({D})/{total_supply}"
    )


D_UNIT = 10**18
positive_balance = st.integers(min_value=10**5 * D_UNIT, max_value=10**11 * D_UNIT)
amplification_coefficient = st.integers(min_value=MIN_A, max_value=MAX_A)
gamma_coefficient = st.integers(min_value=MIN_GAMMA, max_value=MAX_GAMMA)
price = st.integers(min_value=10**12, max_value=10**25)


@given(
    st.integers(min_value=1, max_value=300),
    st.integers(min_value=0, max_value=2),
    st.integers(min_value=0, max_value=2),
)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_exchange(vyper_tricrypto, dx_perc, i, j):
    """Test `exchange` against vyper implementation."""
    assume(i != j)

    pool = initialize_pool(vyper_tricrypto)
    dx = pool.balances[i] * dx_perc // 100

    expected_dy = vyper_tricrypto.exchange(i, j, dx, 0)
    dy, _ = pool.exchange(i, j, dx)
    assert dy == expected_dy

    expected_balances = [vyper_tricrypto.balances(i) for i in range(3)]
    assert pool.balances == expected_balances


_num_iter = 10


@given(
    st.lists(
        st.integers(min_value=1, max_value=10000),
        min_size=_num_iter,
        max_size=_num_iter,
    ),
    st.lists(
        st.tuples(
            st.integers(min_value=0, max_value=2),
            st.integers(min_value=0, max_value=2),
        ).filter(lambda x: x[0] != x[1]),
        min_size=_num_iter,
        max_size=_num_iter,
    ),
    st.lists(
        st.integers(min_value=0, max_value=86400),
        min_size=_num_iter,
        max_size=_num_iter,
    ),
)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_multiple_exchange_with_repeg(
    vyper_tricrypto, dx_perc_list, indices_list, time_delta_list
):
    """Test `exchange` against vyper implementation."""

    pool = initialize_pool(vyper_tricrypto)

    for indices, dx_perc, time_delta in zip(
        indices_list, dx_perc_list, time_delta_list
    ):
        vm_timestamp = boa.env.vm.state.timestamp
        pool._block_timestamp = vm_timestamp

        i, j = indices
        dx = pool.balances[i] * dx_perc // 10000  # dx_perc in bps

        expected_dy = vyper_tricrypto.exchange(i, j, dx, 0)
        dy, _ = pool.exchange(i, j, dx)
        assert dy == expected_dy

        expected_balances = [vyper_tricrypto.balances(i) for i in range(3)]
        assert pool.balances == expected_balances

        assert pool.last_prices == [vyper_tricrypto.last_prices(i) for i in range(2)]
        assert pool.last_prices_timestamp == vyper_tricrypto.last_prices_timestamp()

        expected_price_oracle = [vyper_tricrypto.price_oracle(i) for i in range(2)]
        expected_price_scale = [vyper_tricrypto.price_scale(i) for i in range(2)]
        assert pool.price_oracle() == expected_price_oracle
        assert pool.price_scale == expected_price_scale

        boa.env.time_travel(time_delta)


@given(
    amplification_coefficient,
    gamma_coefficient,
    positive_balance,
    positive_balance,
    positive_balance,
)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_newton_D(vyper_tricrypto, A, gamma, x0, x1, x2):
    """Test D calculation against vyper implementation."""

    xp = [x0, x1, x2]
    assume(0.02 < xp[0] / xp[1] < 50)
    assume(0.02 < xp[1] / xp[2] < 50)
    assume(0.02 < xp[0] / xp[2] < 50)

    MATH = get_math(vyper_tricrypto)
    # pylint: disable=no-member
    expected_D = MATH.newton_D(A, gamma, xp)
    D = newton_D(A, gamma, xp)

    assert D == expected_D


@given(
    amplification_coefficient,
    gamma_coefficient,
    positive_balance,
    positive_balance,
    positive_balance,
)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=2,
    deadline=None,
)
def test_get_p(vyper_tricrypto, A, gamma, x0, x1, x2):
    """Test `get_p` calculation against vyper implementation."""

    xp = [x0, x1, x2]
    assume(0.02 < xp[0] / xp[1] < 50)
    assume(0.02 < xp[1] / xp[2] < 50)
    assume(0.02 < xp[0] / xp[2] < 50)

    MATH = get_math(vyper_tricrypto)
    # pylint: disable=no-member
    D = MATH.newton_D(A, gamma, xp)

    A_gamma = [A, gamma]
    expected_p = MATH.get_p(xp, D, A_gamma)
    p = get_p(xp, D, A, gamma)

    assert p == expected_p


@given(
    amplification_coefficient,
    gamma_coefficient,
    positive_balance,
    positive_balance,
    positive_balance,
    st.tuples(
        st.integers(min_value=0, max_value=2),
        st.integers(min_value=0, max_value=2),
    ).filter(lambda x: x[0] != x[1]),
    st.integers(min_value=1, max_value=10000),
)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_pure_get_y(vyper_tricrypto, A, gamma, x0, x1, x2, pair, dx_perc):
    """Test `get_y` calculation against vyper implementation."""
    i, j = pair

    xp = [x0, x1, x2]
    assume(0.02 < xp[0] / xp[1] < 50)
    assume(0.02 < xp[1] / xp[2] < 50)
    assume(0.02 < xp[0] / xp[2] < 50)

    MATH = get_math(vyper_tricrypto)
    # pylint: disable=no-member
    D = MATH.newton_D(A, gamma, xp)

    xp[i] += xp[i] * dx_perc // 10000

    expected_y_out = MATH.get_y(A, gamma, xp, D, j)
    y_out = get_y(A, gamma, xp, D, j)

    assert y_out[0] == expected_y_out[0]
    assert y_out[1] == expected_y_out[1]


def test_pool_get_y(vyper_tricrypto):
    """
    Test `CurveCryptoPool.get_y`.

    Note the pure version of `get_y` is already tested
    thoroughly in its own test against the vyper.

    This test is a sanity check to make sure we pass values in correctly
    to the pure `get_y` implementation.
    """
    pool = initialize_pool(vyper_tricrypto)

    xp = pool._xp()
    A = pool.A
    gamma = pool.gamma
    D = newton_D(A, gamma, xp)

    i = 0
    j = 1

    # `get_y` will set i-th balance to `x`
    x = xp[i] * 102 // 100
    y = pool.get_y(i, j, x, xp)

    xp[i] = x
    expected_y, _ = get_y(A, gamma, xp, D, j)

    assert y == expected_y


@given(st.integers(min_value=-42139678854452767551, max_value=135305999368893231588))
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=2,
    deadline=None,
)
def test_wad_exp(vyper_tricrypto, x):
    """Test the snekmate wad exp calc"""
    MATH = get_math(vyper_tricrypto)
    # pylint: disable=no-member
    expected_result = MATH.wad_exp(x)
    result = wad_exp(x)
    assert result == expected_result


@given(
    amplification_coefficient,
    gamma_coefficient,
    positive_balance,
    positive_balance,
    positive_balance,
    st.tuples(
        st.integers(min_value=0, max_value=2),
        st.integers(min_value=0, max_value=2),
    ).filter(lambda x: x[0] != x[1]),
    st.integers(min_value=1, max_value=10000),
)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=1,
    deadline=None,
)
def test__newton_y(vyper_tricrypto, A, gamma, x0, x1, x2, pair, dx_perc):
    """Test D calculation against vyper implementation."""
    i, j = pair

    xp = [x0, x1, x2]
    assume(0.02 < xp[0] / xp[1] < 50)
    assume(0.02 < xp[1] / xp[2] < 50)
    assume(0.02 < xp[0] / xp[2] < 50)

    MATH = get_math(vyper_tricrypto)
    # pylint: disable=no-member
    D = MATH.newton_D(A, gamma, xp)

    xp[i] += xp[i] * dx_perc // 10000

    expected_y = MATH.eval(f"self._newton_y({A}, {gamma}, {xp}, {D}, {j})")
    y = _newton_y(A, gamma, xp, D, j)

    assert y == expected_y


def test_dydxfee(vyper_tricrypto):
    """Test spot price formula against execution price for small trades."""
    pool = initialize_pool(vyper_tricrypto)

    # USDT, WBTC, WETH
    decimals = [6, 8, 18]
    precisions = [10 ** (18 - d) for d in decimals]

    # print("WBTC price:", pool.price_scale[0] / 10**18)
    # print("WETH price:", pool.price_scale[1] / 10**18)

    dxs = [
        10**6,
        10**4,
        10**15,
    ]

    for pair in permutations([0, 1, 2], 2):
        i, j = pair

        dydx = pool.dydxfee(i, j)
        dx = dxs[i]
        dy = vyper_tricrypto.exchange(i, j, dx, 0)
        pool.exchange(i, j, dx, 0)  # update state to match vyper pool

        dx *= precisions[i]
        dy *= precisions[j]
        assert abs(dydx - dy / dx) / (dy / dx) < 1e-4
