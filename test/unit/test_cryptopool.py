"""Unit tests for CurveCryptoPool"""
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from curvesim.pool import CurveCryptoPool
from curvesim.pool.cryptoswap.pool import (
    MAX_A,
    MAX_GAMMA,
    MIN_A,
    MIN_GAMMA,
    _geometric_mean,
    _halfpow,
    _sqrt_int,
)


def initialize_pool(vyper_cryptopool):
    """
    Initialize python-based pool from the state variables of the
    vyper-based implementation.
    """
    A = vyper_cryptopool.A()
    gamma = vyper_cryptopool.gamma()
    n_coins = vyper_cryptopool.N_COINS()
    balances = [vyper_cryptopool.balances(i) for i in range(n_coins)]
    precisions = vyper_cryptopool.eval("self._get_precisions()")
    lp_total_supply = vyper_cryptopool.totalSupply()
    mid_fee = vyper_cryptopool.mid_fee()
    out_fee = vyper_cryptopool.out_fee()
    allowed_extra_profit = vyper_cryptopool.allowed_extra_profit()
    fee_gamma = vyper_cryptopool.fee_gamma()
    adjustment_step = vyper_cryptopool.adjustment_step()
    admin_fee = vyper_cryptopool.admin_fee()
    ma_half_time = vyper_cryptopool.ma_half_time()
    price_scale = vyper_cryptopool.price_scale()

    pool = CurveCryptoPool(
        A=A,
        gamma=gamma,
        D=balances,
        n=n_coins,
        precisions=precisions,
        tokens=lp_total_supply,
        mid_fee=mid_fee,
        out_fee=out_fee,
        allowed_extra_profit=allowed_extra_profit,
        fee_gamma=fee_gamma,
        adjustment_step=adjustment_step,
        admin_fee=admin_fee,
        ma_half_time=ma_half_time,
        initial_price=price_scale,
    )

    assert pool.A == vyper_cryptopool.A()
    assert pool.gamma == vyper_cryptopool.gamma()

    return pool


def pack_A_gamma(A, gamma):
    """
    Need this to set A and gamma in the smart contract since they
    are stored in packed format.
    """
    A_gamma = A << 128
    A_gamma = A_gamma | gamma
    return A_gamma


D_UNIT = 10**18
positive_balance = st.integers(min_value=10**4 * D_UNIT, max_value=50**10 * D_UNIT)
amplification_coefficient = st.integers(min_value=MIN_A, max_value=MAX_A)
gamma_coefficient = st.integers(min_value=MIN_GAMMA, max_value=MAX_GAMMA)


@given(positive_balance, positive_balance)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_xp(vyper_cryptopool, x0, x1):
    """Test xp calculation against vyper implementation."""

    _balances = [x0, x1]
    precisions = vyper_cryptopool.eval("self._get_precisions()")
    balances = [x // p for x, p in zip(_balances, precisions)]

    vyper_cryptopool.eval(f"self.balances={balances}")
    expected_xp = vyper_cryptopool.eval("self.xp()")
    expected_xp = list(expected_xp)

    pool = initialize_pool(vyper_cryptopool)
    xp = pool._xp()

    assert xp == expected_xp


@given(positive_balance, positive_balance, st.booleans())
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_geometric_mean(vyper_cryptopool, x0, x1, sort_flag):
    """Test geometric_mean calculation against vyper implementation."""

    _balances = [x0, x1]
    precisions = vyper_cryptopool.eval("self._get_precisions()")
    xp = [x // p for x, p in zip(_balances, precisions)]

    expected_result = vyper_cryptopool.eval(f"self.geometric_mean({xp}, {sort_flag})")
    result = _geometric_mean(xp, sort_flag)

    assert result == expected_result


@given(st.integers(min_value=0))
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_halfpow(vyper_cryptopool, power):
    """Test halfpow calculation against vyper implementation."""

    expected_result = vyper_cryptopool.eval(f"self.halfpow({power})")
    result = _halfpow(power)

    assert result == expected_result


@given(st.integers(min_value=0))
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_sqrt_int(vyper_cryptopool, number):
    """Test sqrt_int calculation against vyper implementation."""

    expected_result = vyper_cryptopool.eval(f"self.sqrt_int({number})")
    result = _sqrt_int(number)

    assert result == expected_result


@given(st.integers(min_value=100))
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_get_xcp(vyper_cryptopool, D):
    """Test get_xcp calculation against vyper implementation."""

    expected_result = vyper_cryptopool.eval(f"self.get_xcp({D})")

    pool = initialize_pool(vyper_cryptopool)
    result = pool._get_xcp(D)  # pylint: disable=protected-access

    assert result == expected_result


@given(amplification_coefficient, gamma_coefficient, positive_balance, positive_balance)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_newton_D(vyper_cryptopool, A, gamma, x0, x1):
    """Test D calculation against vyper implementation."""

    _balances = [x0, x1]
    precisions = vyper_cryptopool.eval("self._get_precisions()")
    balances = [x // p for x, p in zip(_balances, precisions)]

    vyper_cryptopool.eval(f"self.balances={balances}")
    xp = vyper_cryptopool.eval("self.xp()")
    xp = list(xp)
    assume(0.02 < xp[0] / xp[1] < 50)
    expected_D = vyper_cryptopool.eval(f"self.newton_D({A}, {gamma}, {xp})")

    # pylint: disable=protected-access
    D = CurveCryptoPool._newton_D(A, gamma, xp)

    assert D == expected_D


@given(
    amplification_coefficient,
    gamma_coefficient,
    positive_balance,
    positive_balance,
    st.integers(min_value=0, max_value=1),
    st.integers(min_value=0, max_value=25),
)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_newton_y(vyper_cryptopool, A, gamma, x0, x1, i, delta_perc):
    """Test get_y calculation against vyper implementation."""

    _balances = [x0, x1]
    precisions = vyper_cryptopool.eval("self._get_precisions()")
    balances = [x // p for x, p in zip(_balances, precisions)]

    vyper_cryptopool.eval(f"self.balances={balances}")
    xp = vyper_cryptopool.eval("self.xp()")
    xp = list(xp)
    assume(0.02 < xp[0] / xp[1] < 50)

    # vary D by delta_perc %
    D = vyper_cryptopool.eval(f"self.newton_D({A}, {gamma}, {xp})")
    D_changed = D * (100 - delta_perc) // 100
    expected_y = vyper_cryptopool.eval(
        f"self.newton_y({A}, {gamma}, {xp}, {D_changed}, {i})"
    )

    pool = initialize_pool(vyper_cryptopool)
    y = pool._newton_y(A, gamma, xp, D_changed, i)  # pylint: disable=protected-access

    assert y == expected_y

    # vary xp[j] by delta_perc %
    xp_changed = xp.copy()
    j = 1 - i
    xp_changed[j] = xp[j] * (100 - delta_perc) // 100
    expected_y = vyper_cryptopool.eval(
        f"self.newton_y({A}, {gamma}, {xp_changed}, {D}, {i})"
    )

    y = pool._newton_y(A, gamma, xp_changed, D, i)  # pylint: disable=protected-access

    assert y == expected_y


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
def test_tweak_price(vyper_cryptopool, A, gamma, x0, x1, price):
    _balances = [x0, x1]
    precisions = vyper_cryptopool.eval("self._get_precisions()")
    balances = [x // p for x, p in zip(_balances, precisions)]

    vyper_cryptopool.eval(f"self.balances={balances}")
    xp = vyper_cryptopool.eval("self.xp()")
    xp = list(xp)
    assume(0.02 < xp[0] / xp[1] < 50)

    A_gamma = [A, gamma]
    vyper_cryptopool.eval(f"self.tweak_price({A_gamma}, {xp}, {price}, 0)")

    pool = initialize_pool(vyper_cryptopool)
    pool._tweak_price(A, gamma, xp, price, 0)

    assert pool.virtual_price == vyper_cryptopool.virtual_price()
