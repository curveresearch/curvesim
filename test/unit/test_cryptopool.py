"""Unit tests for CurveCryptoPool"""
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from curvesim.pool import CurveCryptoPool


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
    return pool


D_UNIT = 10**18
positive_balance = st.integers(min_value=10**4 * D_UNIT, max_value=50**10 * D_UNIT)


@given(positive_balance, positive_balance)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_newton_D(vyper_cryptopool, x0, x1):
    """Test D calculation against vyper implementation."""

    _balances = [x0, x1]
    precisions = vyper_cryptopool.eval("self._get_precisions()")
    balances = [x // p for x, p in zip(_balances, precisions)]

    vyper_cryptopool.eval(f"self.balances={balances}")
    xp = vyper_cryptopool.eval("self.xp()")
    xp = list(xp)
    A = vyper_cryptopool.A()
    gamma = vyper_cryptopool.gamma()
    expected_D = vyper_cryptopool.eval(f"self.newton_D({A}, {gamma}, {xp})")

    # pylint: disable=protected-access
    pool = initialize_pool(vyper_cryptopool)
    xp = pool._xp()
    A = pool.A
    gamma = pool.gamma
    D = pool._newton_D(A, gamma, xp)

    assert D == expected_D
