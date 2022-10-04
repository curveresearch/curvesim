from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from curvesim.pool import MetaPool

from .test_pool import initialize_pool


def initialize_metapool(vyper_metapool, vyper_3pool):
    """
    Initialize python-based pool from the state variables of the
    vyper-based implementation.
    """
    A = vyper_metapool.A()
    n_coins = vyper_metapool.N_COINS()
    balances = [vyper_metapool.balances(i) for i in range(n_coins)]
    p = [vyper_metapool.rates(i) for i in range(n_coins)]
    lp_total_supply = vyper_metapool.totalSupply()
    fee = vyper_metapool.fee()
    admin_fee = vyper_metapool.admin_fee()
    basepool = initialize_pool(vyper_3pool)
    metapool = MetaPool(
        A,
        D=balances,
        n=n_coins,
        basepool=basepool,
        p=p,
        tokens=lp_total_supply,
        fee=fee,
        admin_fee=admin_fee,
    )
    return metapool


# We can assume the contract works on more extreme values; we only need
# to be reasonably certain our results are consistent, so we can check
# a smaller range.
#
# With 18 decimal precision, it seems reasonable to pick these bounds
D_UNIT = 10**18
positive_balance = st.integers(min_value=10**5 * D_UNIT, max_value=10**10 * D_UNIT)


@given(positive_balance, positive_balance)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=10,
    deadline=400,
)
def test_get_D(vyper_metapool, vyper_3pool, x0, x1):
    """Test D calculation against vyper implementation."""

    _balances = [x0, x1]
    p = [vyper_metapool.rates(i) for i in range(len(_balances))]
    balances = [x * 10**18 // p for x, p in zip(_balances, p)]

    vyper_metapool.eval(f"self.balances={balances}")
    expected_D = vyper_metapool.D()

    python_metapool = initialize_metapool(vyper_metapool, vyper_3pool)
    D = python_metapool.D()

    assert D == expected_D


#
# def test_get_D_balanced():
#     """Sanity check for when pool is perfectly balanced"""
#
#     # create balanced pool
#     balances = [
#         295949605740077000000000000,
#         295949605740077,
#         295949605740077,
#     ]
#     p = [10**18, 10**30, 10**30]
#     n_coins = 3
#     A = 5858
#
#     pool = Pool(A, D=balances, n=n_coins, p=p)
#     D = pool.D()
#
#     virtualized_balances = [b * p // 10**18 for b, p in zip(balances, p)]
#     expected_D = sum(virtualized_balances)
#
#     assert D == expected_D
#
#
# def test_get_virtual_price(vyper_3pool):
#     """Test `get_virtual_price` against vyper implementation."""
#
#     python_3pool = initialize_pool(vyper_3pool)
#     virtual_price = python_3pool.get_virtual_price()
#     expected_virtual_price = vyper_3pool.get_virtual_price()
#     assert virtual_price == expected_virtual_price
#
#
# def test_get_y(vyper_3pool, mainnet_3pool_state):
#     """Test y calculation against vyper implementation"""
#
#     virtual_balances = mainnet_3pool_state["virtual_balances"]
#
#     i = 0
#     j = 1
#     x = 516 * 10**18
#     # need `eval` since this function is internal
#     expected_y = vyper_3pool.eval(f"self.get_y({i}, {j}, {x}, {virtual_balances})")
#
#     python_3pool = initialize_pool(vyper_3pool)
#     y = python_3pool.get_y(i, j, x, virtual_balances)
#     assert y == expected_y
#
def test_get_virtual_price(vyper_metapool, vyper_3pool):
    """Test `get_virtual_price` against vyper implementation."""
    python_metapool = initialize_metapool(vyper_metapool, vyper_3pool)
    virtual_price = python_metapool.get_virtual_price()
    expected_virtual_price = vyper_metapool.get_virtual_price()
    assert virtual_price == expected_virtual_price


#
# def test_get_y_D(vyper_3pool):
#     """Test y calculation against vyper implementation"""
#
#     python_3pool = initialize_pool(vyper_3pool)
#     A = python_3pool.A
#     virtual_balances = python_3pool.xp()
#     D = python_3pool.D()
#
#     i = 0
#     j = 1
#     dx = 516 * 10**18
#     virtual_balances[j] += dx
#     expected_y = vyper_3pool.eval(f"self.get_y_D({A}, {i}, {virtual_balances}, {D})")
#
#     y = python_3pool.get_y_D(A, i, virtual_balances, D)
#     assert y == expected_y
#
#
# @given(positive_balance, positive_balance, positive_balance)
# @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10)
# def test_calc_token_amount(vyper_3pool, x0, x1, x2):
#     """Test `calc_token_amount` against vyper implementation."""
#     python_3pool = initialize_pool(vyper_3pool)
#
#     _balances = [x0, x1, x2]
#     rates = [vyper_3pool.rates(i) for i in range(len(_balances))]
#     balances = [b * 10**18 // r for b, r in zip(_balances, rates)]
#
#     expected_lp_amount = vyper_3pool.calc_token_amount(balances, True)
#     lp_amount = python_3pool.calc_token_amount(balances)
#
#     assert lp_amount == expected_lp_amount
#
#
# @given(positive_balance, positive_balance, positive_balance)
# @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10)
# def test_add_liquidity(vyper_3pool, x0, x1, x2):
#     """Test `add_liquidity` against vyper implementation."""
#     python_3pool = initialize_pool(vyper_3pool)
#
#     _balances = [x0, x1, x2]
#     rates = [vyper_3pool.rates(i) for i in range(len(_balances))]
#     amounts = [b * 10**18 // r for b, r in zip(_balances, rates)]
#
#     old_vyper_balances = [vyper_3pool.balances(i) for i in range(len(_balances))]
#     balances = python_3pool.x
#     assert balances == old_vyper_balances
#
#     lp_total_supply = vyper_3pool.totalSupply()
#     vyper_3pool.add_liquidity(amounts, 0)
#     expected_lp_amount = vyper_3pool.totalSupply() - lp_total_supply
#
#     lp_amount = python_3pool.add_liquidity(amounts)
#     assert lp_amount == expected_lp_amount
#
#     expected_balances = [vyper_3pool.balances(i) for i in range(len(_balances))]
#     new_balances = python_3pool.x
#     assert new_balances == expected_balances
#
#
# @given(
#     positive_balance,
#     st.integers(min_value=0, max_value=2),
#     st.integers(min_value=0, max_value=2),
# )
# @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10)
# def test_exchange(vyper_3pool, dx, i, j):
#     """Test `exchange` against vyper implementation."""
#     assume(i != j)
#
#     python_3pool = initialize_pool(vyper_3pool)
#
#     old_vyper_balances = [vyper_3pool.balances(i) for i in range(3)]
#     balances = python_3pool.x
#     assert balances == old_vyper_balances
#
#     # convert to real units
#     dx = dx * 10**18 // vyper_3pool.rates(i)
#
#     expected_dy = vyper_3pool.exchange(i, j, dx, 0)
#     dy, _ = python_3pool.exchange(i, j, dx)
#
#     assert dy == expected_dy
#
#     expected_balances = [vyper_3pool.balances(i) for i in range(3)]
#     new_balances = python_3pool.x
#     assert new_balances == expected_balances
#
#
# @given(positive_balance, st.integers(min_value=0, max_value=2))
# @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10)
# def test_calc_withdraw_one_token(vyper_3pool, amount, i):
#     """Test `calc_withdraw_one_coin` against vyper implementation."""
#     assume(amount < vyper_3pool.totalSupply())
#
#     python_3pool = initialize_pool(vyper_3pool)
#
#     expected_coin_amount = vyper_3pool.calc_withdraw_one_coin(amount, i)
#     coin_amount, _ = python_3pool.calc_withdraw_one_coin(amount, i)
#     assert coin_amount == expected_coin_amount
#
#
# @given(positive_balance, st.integers(min_value=0, max_value=2))
# @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10)
# def test_remove_liquidity_one_coin(vyper_3pool, amount, i):
#     """Test `remove_liquidity_one_coin` against vyper implementation."""
#     assume(amount < vyper_3pool.totalSupply())
#
#     python_3pool = initialize_pool(vyper_3pool)
#
#     old_vyper_balances = [vyper_3pool.balances(i) for i in range(3)]
#     balances = python_3pool.x
#     assert balances == old_vyper_balances
#
#     old_vyper_supply = vyper_3pool.totalSupply()
#     lp_supply = python_3pool.tokens
#     assert lp_supply == old_vyper_supply
#
#     vyper_3pool.remove_liquidity_one_coin(amount, i, 0)
#     expected_coin_balance = vyper_3pool.balances(i)
#     expected_lp_supply = vyper_3pool.totalSupply()
#
#     python_3pool.remove_liquidity_one_coin(amount, i)
#     coin_balance = python_3pool.x[i]
#     lp_supply = python_3pool.tokens
#
#     assert coin_balance == expected_coin_balance
#     assert lp_supply == expected_lp_supply
