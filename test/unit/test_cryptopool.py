"""Unit tests for CurveCryptoPool"""
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from curvesim.pool import CurveCryptoPool


def initialize_pool(vyper_pool):
    """
    Initialize python-based pool from the state variables of the
    vyper-based implementation.
    """
    A = vyper_pool.A()
    n_coins = vyper_pool.N_COINS()
    balances = [vyper_pool.balances(i) for i in range(n_coins)]
    rates = [vyper_pool.rates(i) for i in range(n_coins)]
    lp_total_supply = vyper_pool.totalSupply()
    fee = vyper_pool.fee()
    admin_fee = vyper_pool.admin_fee()
    pool = CurveCryptoPool(
        A,
        D=balances,
        n=n_coins,
        rates=rates,
        tokens=lp_total_supply,
        fee=fee,
        admin_fee=admin_fee,
    )
    return pool


def test_get_D_against_prod(vyper_3pool, mainnet_3pool_state):
    """
    Test boa value against live contract.

    This checks boa is working correctly and also ensures mainnet
    state stays consistent.
    """
    # Compare against virtual price since that's exposed externally
    # while `get_D` is internal in the contract.
    D = vyper_3pool.D()
    total_supply = mainnet_3pool_state["lp_tokens"]
    virtual_price = D * 10**18 // total_supply

    expected_virtual_price = mainnet_3pool_state["virtual_price"]
    assert virtual_price == expected_virtual_price


def test_get_D_mainnet(vyper_3pool):
    """
    Test D calculation against vyper implementation using
    mainnet state.
    """
    expected_D = vyper_3pool.D()

    python_3pool = initialize_pool(vyper_3pool)
    D = python_3pool.D()

    assert D == expected_D


# We can assume the contract works on more extreme values; we only need
# to be reasonably certain our results are consistent, so we can check
# a smaller range.
#
# With 18 decimal precision, it seems reasonable to pick these bounds
D_UNIT = 10**18
positive_balance = st.integers(min_value=10**5 * D_UNIT, max_value=10**10 * D_UNIT)


@given(positive_balance, positive_balance, positive_balance)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_get_D(vyper_3pool, x0, x1, x2):
    """Test D calculation against vyper implementation."""

    _balances = [x0, x1, x2]
    p = [vyper_3pool.rates(i) for i in range(len(_balances))]
    balances = [x * 10**18 // p for x, p in zip(_balances, p)]

    vyper_3pool.eval(f"self.balances={balances}")
    expected_D = vyper_3pool.D()

    pool = initialize_pool(vyper_3pool)
    D = pool.D()

    assert D == expected_D
