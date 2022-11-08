import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from curvesim.pool import CurveMetaPool, CurvePool

from .test_pool import initialize_pool


def convert_to_virtual_balances(rates, balances):
    return [b * p // 10**18 for b, p in zip(balances, rates)]


def convert_to_real_balances(rates, balances):
    return [b * 10**18 // p for b, p in zip(balances, rates)]


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
    metapool = CurveMetaPool(
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
    max_examples=5,
    deadline=None,
)
def test_get_D(vyper_metapool, vyper_3pool, x0, x1):
    """Test D calculation against vyper implementation."""

    _balances = [x0, x1]
    p = [vyper_metapool.rates(i) for i in range(len(_balances))]
    balances = convert_to_real_balances(p, _balances)

    vyper_metapool.eval(f"self.balances={balances}")
    expected_D = vyper_metapool.D()

    python_metapool = initialize_metapool(vyper_metapool, vyper_3pool)
    D = python_metapool.D()

    assert D == expected_D


def test_get_virtual_price(vyper_metapool, vyper_3pool):
    """Test `get_virtual_price` against vyper implementation."""
    python_metapool = initialize_metapool(vyper_metapool, vyper_3pool)
    virtual_price = python_metapool.get_virtual_price()
    expected_virtual_price = vyper_metapool.get_virtual_price()
    assert virtual_price == expected_virtual_price


@given(
    positive_balance,
    st.integers(min_value=0, max_value=1),
    st.integers(min_value=0, max_value=1),
)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_get_y(vyper_metapool, vyper_3pool, x, i, j):
    """Test y calculation against vyper implementation"""
    assume(i != j)

    balances = [vyper_metapool.balances(i) for i in range(2)]
    rates = [vyper_metapool.rates(i) for i in range(2)]
    virtual_balances = convert_to_virtual_balances(rates, balances)

    # need `eval` since this function is internal
    expected_y = vyper_metapool.eval(f"self.get_y({i}, {j}, {x}, {virtual_balances})")

    python_metapool = initialize_metapool(vyper_metapool, vyper_3pool)
    y = python_metapool.get_y(i, j, x, virtual_balances)
    assert y == expected_y


@given(
    st.integers(min_value=10 * D_UNIT, max_value=10**6 * D_UNIT),
    st.integers(min_value=0, max_value=1),
    st.integers(min_value=0, max_value=1),
)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_get_y_D(vyper_metapool, vyper_3pool, dx, i, j):
    """Test y calculation against vyper implementation"""
    assume(i != j)

    python_metapool = initialize_metapool(vyper_metapool, vyper_3pool)
    A = python_metapool.A
    D = python_metapool.D()
    rates = python_metapool.rates()
    balances = python_metapool.x
    vyper_balances = [vyper_metapool.balances(i) for i in range(2)]
    assert balances == vyper_balances
    virtual_balances = convert_to_virtual_balances(rates, balances)

    virtual_balances[j] += dx

    # Need `eval` since this function is internal.
    # `get_y_D` also takes in A_precise not A.
    A_precise = A * 100
    expected_y = vyper_metapool.eval(
        f"self.get_y_D({A_precise}, {i}, {virtual_balances}, {D})"
    )

    y = python_metapool.get_y_D(A, i, virtual_balances, D)
    assert y == expected_y


@given(positive_balance, positive_balance)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_calc_token_amount(vyper_metapool, vyper_3pool, x0, x1):
    """Test `calc_token_amount` against vyper implementation."""
    python_metapool = initialize_metapool(vyper_metapool, vyper_3pool)

    _balances = [x0, x1]
    rates = [vyper_metapool.rates(i) for i in range(len(_balances))]
    balances = convert_to_real_balances(rates, _balances)

    expected_lp_amount = vyper_metapool.calc_token_amount(balances, True)
    lp_amount = python_metapool.calc_token_amount(balances)

    assert lp_amount == expected_lp_amount


@given(positive_balance, positive_balance)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_add_liquidity(vyper_metapool, vyper_3pool, x0, x1):
    """Test `add_liquidity` against vyper implementation."""
    python_metapool = initialize_metapool(vyper_metapool, vyper_3pool)

    _balances = [x0, x1]
    rates = [vyper_metapool.rates(i) for i in range(len(_balances))]
    amounts = convert_to_real_balances(rates, _balances)

    old_vyper_balances = [vyper_metapool.balances(i) for i in range(len(_balances))]
    balances = python_metapool.x
    assert balances == old_vyper_balances

    lp_total_supply = vyper_metapool.totalSupply()
    vyper_metapool.add_liquidity(amounts, 0)
    expected_lp_amount = vyper_metapool.totalSupply() - lp_total_supply

    lp_amount = python_metapool.add_liquidity(amounts)
    assert lp_amount == expected_lp_amount

    expected_balances = [vyper_metapool.balances(i) for i in range(len(_balances))]
    new_balances = python_metapool.x
    assert new_balances == expected_balances


@given(
    positive_balance,
    st.integers(min_value=0, max_value=1),
    st.integers(min_value=0, max_value=1),
)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_exchange(vyper_metapool, vyper_3pool, dx, i, j):
    """Test `exchange` against vyper implementation."""
    assume(i != j)

    python_metapool = initialize_metapool(vyper_metapool, vyper_3pool)

    old_vyper_balances = [vyper_metapool.balances(i) for i in range(2)]
    balances = python_metapool.x
    assert balances == old_vyper_balances

    # convert to real units
    dx = dx * 10**18 // vyper_metapool.rates(i)

    expected_dy = vyper_metapool.exchange(i, j, dx, 0)
    dy, _ = python_metapool.exchange(i, j, dx)

    assert dy == expected_dy

    expected_balances = [vyper_metapool.balances(i) for i in range(2)]
    new_balances = python_metapool.x
    assert new_balances == expected_balances


@given(
    positive_balance,
    st.integers(min_value=0, max_value=3),
    st.integers(min_value=0, max_value=3),
)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_exchange_underlying(vyper_metapool, vyper_3pool, dx, i, j):
    """Test `exchange_underlying` against vyper implementation."""
    assume(i != j)

    python_metapool = initialize_metapool(vyper_metapool, vyper_3pool)
    python_basepool = python_metapool.basepool

    # check metapool balances
    old_vyper_balances = [vyper_metapool.balances(i) for i in range(2)]
    balances = python_metapool.x
    assert balances == old_vyper_balances
    # check basepool balances
    old_vyper_balances = [vyper_3pool.balances(i) for i in range(3)]
    balances = python_basepool.x
    assert balances == old_vyper_balances

    # convert to real units
    if i == 0:
        dx = dx * 10**18 // vyper_metapool.rates(0)
    else:
        base_i = i - 1
        dx = dx * 10**18 // vyper_3pool.rates(base_i)

    expected_dy = vyper_metapool.exchange_underlying(i, j, dx, 0)
    dy, _ = python_metapool.exchange_underlying(i, j, dx)

    assert dy == expected_dy

    # check metapool balances
    expected_balances = [vyper_metapool.balances(i) for i in range(2)]
    new_balances = python_metapool.x
    assert new_balances == expected_balances
    # check basepool balances
    expected_balances = [vyper_3pool.balances(i) for i in range(3)]
    new_balances = python_basepool.x
    assert new_balances == expected_balances


@given(positive_balance, st.integers(min_value=0, max_value=1))
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_calc_withdraw_one_token(vyper_metapool, vyper_3pool, amount, i):
    """Test `calc_withdraw_one_coin` against vyper implementation."""
    assume(amount < vyper_metapool.totalSupply())

    python_metapool = initialize_metapool(vyper_metapool, vyper_3pool)

    expected_coin_amount = vyper_metapool.calc_withdraw_one_coin(amount, i)
    coin_amount, _ = python_metapool.calc_withdraw_one_coin(amount, i)
    assert coin_amount == expected_coin_amount


@given(positive_balance, st.integers(min_value=0, max_value=1))
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_remove_liquidity_one_coin(vyper_metapool, vyper_3pool, amount, i):
    """Test `remove_liquidity_one_coin` against vyper implementation."""
    assume(amount < vyper_metapool.totalSupply())

    python_metapool = initialize_metapool(vyper_metapool, vyper_3pool)

    old_vyper_balances = [vyper_metapool.balances(i) for i in range(2)]
    balances = python_metapool.x
    assert balances == old_vyper_balances

    old_vyper_supply = vyper_metapool.totalSupply()
    lp_supply = python_metapool.tokens
    assert lp_supply == old_vyper_supply

    vyper_metapool.remove_liquidity_one_coin(amount, i, 0)
    expected_coin_balance = vyper_metapool.balances(i)
    expected_lp_supply = vyper_metapool.totalSupply()

    python_metapool.remove_liquidity_one_coin(amount, i)
    coin_balance = python_metapool.x[i]
    lp_supply = python_metapool.tokens

    assert coin_balance == expected_coin_balance
    assert lp_supply == expected_lp_supply


@pytest.mark.skip(reason="WIP: various issues affecting reliabililty of test")
@given(
    positive_balance,
    positive_balance,
    positive_balance,
    positive_balance,
    positive_balance,
    st.integers(min_value=0, max_value=3),
    st.integers(min_value=0, max_value=3),
)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=10,
    deadline=None,
)
def test_dydxfee(x0, x1, b0, b1, b2, i, j):
    """Test `dydxfee` against discrete pricing using `exchange`"""
    # don't test between base underlyers here; will be done in regular pool tests
    assume(i != j and (i == 0 or j == 0))

    admin_fee = 5 * 10**9

    base_A = 3000
    base_p = [10**18, 10**30, 10**30]
    base_balances = [b0, b1, b2]
    base_balances = convert_to_real_balances(base_p, base_balances)
    base_n = len(base_balances)
    base_tokens = sum(base_balances)
    base_fee = 1 * 10**6
    base_fee = 0
    basepool = CurvePool(
        base_A,
        D=base_balances,
        n=base_n,
        p=base_p,
        tokens=base_tokens,
        fee=base_fee,
        admin_fee=admin_fee,
    )

    A = 1365
    p = [10**18, 10**18]
    balances = [x0, x1]
    balances = convert_to_real_balances(p, balances)
    n = len(balances)
    tokens = sum(balances)
    fee = 4 * 10**6
    fee = 0
    metapool = CurveMetaPool(
        A,
        D=balances,
        n=n,
        basepool=basepool,
        p=p,
        tokens=tokens,
        fee=fee,
        admin_fee=admin_fee,
    )

    _dydx = metapool.dydxfee(i, j)

    rates = p[:1] + base_p
    _dx = 10**12
    dx = _dx * 10**18 // rates[i]
    dy, _ = metapool.exchange_underlying(i, j, dx)
    _dy = dy * rates[j] // 10**18

    price = _dy / _dx
    # print("\n")
    # print("Discretized derivative:", price)
    # print("Continuous derivative:", _dydx)
    # print(f"dx: {dx}, i: {i} ")
    # print(f"dy: {dy}, j: {j} ")
    # print(base_balances)
    # print(balances)
    # print("-------------------------------")

    assert _dydx > 0
    assert price > 0

    tol = 1e-12
    if i == 0:
        # due to our fee approximation for the continuous pricing case,
        # we won't get as much precision with using `exchange_underlying`,
        # which will use the exact fee logic in the contracts.
        tol = 0.0015

    assert abs(price - _dydx) < tol
