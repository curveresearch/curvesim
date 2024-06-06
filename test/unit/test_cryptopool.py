"""Unit tests for CurveCryptoPool"""
import boa
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from curvesim.pool import CurveCryptoPool
from curvesim.pool.cryptoswap.calcs import get_y, halfpow, newton_D
from curvesim.pool.cryptoswap.calcs.factory_2_coin import (
    MAX_A,
    MAX_GAMMA,
    MIN_A,
    MIN_GAMMA,
    PRECISION,
    _sqrt_int,
    geometric_mean,
)
from curvesim.exceptions import CalculationError


def initialize_pool(vyper_cryptopool):
    """
    Initialize python-based pool from the state variables of the
    vyper-based implementation.
    """
    A = vyper_cryptopool.A()
    gamma = vyper_cryptopool.gamma()
    n_coins = vyper_cryptopool.N_COINS()
    precisions = vyper_cryptopool.eval("self._get_precisions()")
    mid_fee = vyper_cryptopool.mid_fee()
    out_fee = vyper_cryptopool.out_fee()
    allowed_extra_profit = vyper_cryptopool.allowed_extra_profit()
    fee_gamma = vyper_cryptopool.fee_gamma()
    adjustment_step = vyper_cryptopool.adjustment_step()
    admin_fee = vyper_cryptopool.admin_fee()
    ma_half_time = vyper_cryptopool.ma_half_time()
    price_scale = vyper_cryptopool.price_scale()
    price_oracle = vyper_cryptopool.eval("self._price_oracle")
    last_prices = vyper_cryptopool.last_prices()
    last_prices_timestamp = vyper_cryptopool.last_prices_timestamp()
    balances = [vyper_cryptopool.balances(i) for i in range(n_coins)]
    # Use the cached `D`. See warning for `virtual_price` below
    D = vyper_cryptopool.D()
    lp_total_supply = vyper_cryptopool.totalSupply()
    xcp_profit = vyper_cryptopool.xcp_profit()
    xcp_profit_a = vyper_cryptopool.xcp_profit_a()

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
        price_scale=[price_scale],
        price_oracle=[price_oracle],
        last_prices=[last_prices],
        last_prices_timestamp=last_prices_timestamp,
        balances=balances,
        D=D,
        tokens=lp_total_supply,
        xcp_profit=xcp_profit,
        xcp_profit_a=xcp_profit_a,
    )

    assert pool.A == vyper_cryptopool.A()
    assert pool.gamma == vyper_cryptopool.gamma()
    assert pool.balances == balances
    assert pool.price_scale == [price_scale]
    assert pool._price_oracle == [price_oracle]  # pylint: disable=protected-access
    assert pool.last_prices == [last_prices]
    assert pool.last_prices_timestamp == last_prices_timestamp
    assert pool.D == vyper_cryptopool.D()
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
    virtual_price = vyper_cryptopool.virtual_price()
    pool.virtual_price = virtual_price

    return pool


def sync_ema_logic(
    vyper_cryptopool,
    pool,
    last_prices,
):
    """
    Test helper to synchronize state variables needed for EMA update.

    This is needed because the local evm block timestamp will drift
    from the python pool's internal timestamp.
    """
    # pylint: disable=protected-access
    price_oracle = vyper_cryptopool.eval("self._price_oracle")
    pool._price_oracle = [price_oracle]

    # synchronize the times between the two pools and reset
    # last_prices and last_prices_timestamp
    vyper_cryptopool.eval(f"self.last_prices={last_prices}")
    pool.last_prices = [last_prices]

    vm_timestamp = boa.env.vm.state.timestamp
    pool._increment_timestamp(timestamp=vm_timestamp)

    last_prices_timestamp = vm_timestamp - 120
    vyper_cryptopool.eval(f"self.last_prices_timestamp={last_prices_timestamp}")
    pool.last_prices_timestamp = last_prices_timestamp


def pack_A_gamma(A, gamma):
    """
    Need this to set A and gamma in the smart contract since they
    are stored in packed format.
    """
    A_gamma = A << 128
    A_gamma = A_gamma | gamma
    return A_gamma


def get_real_balances(virtual_balances, precisions, price_scale):
    """
    Convert from units of D to native token units using the
    given price scale.
    """
    assert len(virtual_balances) == 2
    balances = [x // p for x, p in zip(virtual_balances, precisions)]
    balances[1] = balances[1] * PRECISION // price_scale
    return balances


def update_cached_values(vyper_cryptopool):
    """
    Useful test helper after we manipulate the pool state.

    Calculates `D` and `virtual_price` from pool state and caches
    them in the appropriate storage.
    """
    A = vyper_cryptopool.A()
    gamma = vyper_cryptopool.gamma()
    xp = vyper_cryptopool.eval("self.xp()")
    xp = list(xp)  # boa doesn't like its own tuple wrapper
    D = vyper_cryptopool.eval(f"self.newton_D({A}, {gamma}, {xp})")
    vyper_cryptopool.eval(f"self.D={D}")
    total_supply = vyper_cryptopool.totalSupply()
    vyper_cryptopool.eval(
        f"self.virtual_price=10**18 * self.get_xcp({D})/{total_supply}"
    )


D_UNIT = 10**18
positive_balance = st.integers(min_value=10**5 * D_UNIT, max_value=10**11 * D_UNIT)
amplification_coefficient = st.integers(min_value=MIN_A, max_value=MAX_A)
gamma_coefficient = st.integers(min_value=MIN_GAMMA, max_value=MAX_GAMMA)
price = st.integers(min_value=10**12, max_value=10**25)
bps_change = st.integers(min_value=0, max_value=100 * 100)


@given(positive_balance, positive_balance)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=2,
    deadline=None,
)
def test_xp(vyper_cryptopool, x0, x1):
    """Test xp calculation against vyper implementation."""

    _balances = [x0, x1]
    precisions = vyper_cryptopool.eval("self._get_precisions()")
    price_scale = vyper_cryptopool.price_scale()
    balances = get_real_balances(_balances, precisions, price_scale)

    vyper_cryptopool.eval(f"self.balances={balances}")
    expected_xp = vyper_cryptopool.eval("self.xp()")
    expected_xp = list(expected_xp)

    pool = initialize_pool(vyper_cryptopool)
    xp = pool._xp()  # pylint: disable=protected-access

    assert xp == expected_xp


@given(positive_balance, positive_balance, st.booleans())
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=2,
    deadline=None,
)
def test_geometric_mean(vyper_cryptopool, x0, x1, sort_flag):
    """Test geometric_mean calculation against vyper implementation."""

    xp = [x0, x1]
    expected_result = vyper_cryptopool.eval(f"self.geometric_mean({xp}, {sort_flag})")
    result = geometric_mean(xp, sort_flag)

    assert result == expected_result


@given(st.integers(min_value=0))
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=2,
    deadline=None,
)
def test_halfpow(vyper_cryptopool, power):
    """Test halfpow calculation against vyper implementation."""

    expected_result = vyper_cryptopool.eval(f"self.halfpow({power})")
    result = halfpow(power)

    assert result == expected_result


@given(st.integers(min_value=0))
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=2,
    deadline=None,
)
def test_sqrt_int(vyper_cryptopool, number):
    """Test sqrt_int calculation against vyper implementation."""

    expected_result = vyper_cryptopool.eval(f"self.sqrt_int({number})")
    result = _sqrt_int(number)  # pylint: disable=protected-access

    assert result == expected_result


@given(st.integers(min_value=100))
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=2,
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

    xp = [x0, x1]
    assume(0.02 < xp[0] / xp[1] < 50)

    expected_D = vyper_cryptopool.eval(f"self.newton_D({A}, {gamma}, {xp})")
    D = newton_D(A, gamma, xp)

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
def test_get_y(vyper_cryptopool, A, gamma, x0, x1, i, delta_perc):
    """Test get_y calculation against vyper implementation."""

    xp = [x0, x1]
    assume(0.02 < xp[0] / xp[1] < 50)

    # vary D by delta_perc %
    D = vyper_cryptopool.eval(f"self.newton_D({A}, {gamma}, {xp})")
    D_changed = D * (100 - delta_perc) // 100
    expected_y = vyper_cryptopool.eval(
        f"self.newton_y({A}, {gamma}, {xp}, {D_changed}, {i})"
    )

    y, _ = get_y(A, gamma, xp, D_changed, i)

    assert y == expected_y

    # vary xp[j] by delta_perc %
    xp_changed = xp.copy()
    j = 1 - i
    xp_changed[j] = xp[j] * (100 - delta_perc) // 100
    expected_y = vyper_cryptopool.eval(
        f"self.newton_y({A}, {gamma}, {xp_changed}, {D}, {i})"
    )

    y, _ = get_y(A, gamma, xp_changed, D, i)

    assert y == expected_y


@given(
    amplification_coefficient,
    gamma_coefficient,
    st.integers(min_value=10**6 * D_UNIT, max_value=10**9 * D_UNIT),
    st.integers(min_value=10, max_value=1000),
    st.integers(min_value=70, max_value=200).filter(lambda x: x < 90 or x > 110),
)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_tweak_price(
    vyper_cryptopool, cryptopool_lp_token, A, gamma, x0, x_perc, price_perc
):
    """Test _tweak_price against vyper implementation."""
    # def test_tweak_price(vyper_cryptopool, cryptopool_lp_token):
    #     A = 4196
    #     gamma = 10000050055
    #     x0 = 100000000000000000017267
    #     x1 = 100000000000000000000153
    #     last_price = 1000000000219

    # pylint: disable=protected-access
    x1 = x0 * x_perc // 100
    _balances = [x0, x1]
    price_oracle = vyper_cryptopool.eval("self._price_oracle")
    last_price = price_oracle * price_perc // 100

    precisions = vyper_cryptopool.eval("self._get_precisions()")
    price_scale = vyper_cryptopool.price_scale()
    balances = get_real_balances(_balances, precisions, price_scale)

    vyper_cryptopool.eval(f"self.balances={balances}")
    xp = vyper_cryptopool.eval("self.xp()")
    xp = list(xp)

    A_gamma = [A, gamma]
    # need to set A_gamma since this is read when claiming admin fees
    A_gamma_packed = pack_A_gamma(A, gamma)
    vyper_cryptopool.eval(f"self.future_A_gamma={A_gamma_packed}")

    # need to update cached `D` and `virtual_price`
    # (this requires adjusting LP token supply for consistency)
    D = vyper_cryptopool.eval(f"self.newton_D({A}, {gamma}, {xp})")
    vyper_cryptopool.eval(f"self.D={D}")

    totalSupply = vyper_cryptopool.eval(f"self.get_xcp({D})")
    cryptopool_lp_token.eval(f"self.totalSupply={totalSupply}")
    # virtual price can't be below 10**18
    vyper_cryptopool.eval("self.virtual_price=10**18")
    # reset profit counter also
    vyper_cryptopool.eval("self.xcp_profit=10**18")
    vyper_cryptopool.eval("self.xcp_profit_a=10**18")

    pool = initialize_pool(vyper_cryptopool)

    # ------- test no oracle update and no scale adjustment ------------- #
    assert pool.price_scale == [vyper_cryptopool.price_scale()]
    assert pool._price_oracle == [vyper_cryptopool.eval("self._price_oracle")]

    old_scale = pool.price_scale
    assert old_scale == pool._price_oracle

    old_oracle = pool._price_oracle

    # pylint: disable=protected-access
    try:
        pool._tweak_price(A, gamma, xp, 1, 0, 0)
    except Exception as err:
        assert isinstance(err, CalculationError)
    pool._tweak_price(A, gamma, xp, 1, last_price, None)
    vyper_cryptopool.eval(f"self.tweak_price({A_gamma}, {xp}, {last_price}, 0)")

    assert pool.price_scale == [vyper_cryptopool.price_scale()]
    # no price adjustment since price oracle is same as price scale (`norm` is 0)
    assert pool.price_scale == old_scale
    # EMA price oracle won't update if price oracle and last price is the same
    assert old_oracle == pool._price_oracle

    # ------- test oracle updates with no scale adjustment ------------- #

    sync_ema_logic(vyper_cryptopool, pool, last_price)

    assert pool.virtual_price == vyper_cryptopool.virtual_price()
    assert pool.xcp_profit == vyper_cryptopool.xcp_profit()

    old_oracle = pool._price_oracle
    old_scale = pool.price_scale
    old_virtual_price = pool.virtual_price

    pool._tweak_price(A, gamma, xp, 1, last_price, None)
    vyper_cryptopool.eval(f"self.tweak_price({A_gamma}, {xp}, {last_price}, 0)")

    # check the pools are the same
    assert pool.price_scale == [vyper_cryptopool.price_scale()]
    assert pool._price_oracle == [vyper_cryptopool.eval("self._price_oracle")]
    assert pool.virtual_price == vyper_cryptopool.virtual_price()
    assert pool.D == vyper_cryptopool.D()

    # check oracle updated
    # scale shouldn't change because no adjustment is possible
    # with no profit
    assert pool._price_oracle != old_oracle
    assert pool.price_scale == old_scale
    assert pool.virtual_price == old_virtual_price

    # ------- test scale adjustment ----------------------- #
    sync_ema_logic(vyper_cryptopool, pool, last_price)

    assert pool.price_scale != pool._price_oracle

    old_oracle = pool._price_oracle
    old_scale = pool.price_scale
    old_virtual_price = pool.virtual_price

    xp[0] = xp[0] + pool.allowed_extra_profit // 10

    # omitting price will calculate the spot price in `tweak_price`
    pool._tweak_price(A, gamma, xp, 1, None, None)
    vyper_cryptopool.eval(f"self.tweak_price({A_gamma}, {xp}, 0, 0)")

    assert pool.price_scale == [vyper_cryptopool.price_scale()]
    assert pool._price_oracle == [vyper_cryptopool.eval("self._price_oracle")]

    assert pool.D == vyper_cryptopool.D()
    assert pool.virtual_price == vyper_cryptopool.virtual_price()
    assert pool.xcp_profit == vyper_cryptopool.xcp_profit()

    # profit increased but not enough to adjust the price scale
    assert pool.virtual_price > old_virtual_price
    assert pool.price_scale == old_scale

    old_virtual_price = pool.virtual_price

    xp[0] = xp[0] * 115 // 100

    # omitting price will calculate the spot price in `tweak_price`
    pool._tweak_price(A, gamma, xp, 1, None, None)
    vyper_cryptopool.eval(f"self.tweak_price({A_gamma}, {xp}, 0, 0)")

    assert pool.price_scale == [vyper_cryptopool.price_scale()]
    assert pool._price_oracle == [vyper_cryptopool.eval("self._price_oracle")]

    assert pool.D == vyper_cryptopool.D()
    assert pool.virtual_price == vyper_cryptopool.virtual_price()
    assert pool.xcp_profit == vyper_cryptopool.xcp_profit()

    # profit increased enough to adjust the price scale
    assert pool.virtual_price > old_virtual_price
    assert pool.price_scale != old_scale


@given(
    positive_balance,
    positive_balance,
    st.integers(min_value=1, max_value=10**4),
    st.integers(min_value=0, max_value=1),
)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_get_dy(vyper_cryptopool, x0, x1, dx_perc, i):
    """Test get_dy calculation against vyper implementation."""
    assume(0.02 < x0 / x1 < 50)

    n_coins = 2
    j = 1 - i
    xp = [x0, x1]

    precisions = vyper_cryptopool.eval("self._get_precisions()")
    price_scale = vyper_cryptopool.price_scale()
    balances = get_real_balances(xp, precisions, price_scale)

    vyper_cryptopool.eval(f"self.balances={balances}")
    update_cached_values(vyper_cryptopool)
    pool = initialize_pool(vyper_cryptopool)

    dx = balances[i] * dx_perc // 10**4

    expected_dy = vyper_cryptopool.get_dy(i, j, dx)
    dy = pool.get_dy(i, j, dx)

    assert dy == expected_dy

    expected_balances = [vyper_cryptopool.balances(i) for i in range(n_coins)]
    assert pool.balances == expected_balances


@given(
    st.integers(min_value=1, max_value=300),
    st.integers(min_value=0, max_value=1),
)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_exchange(vyper_cryptopool, dx_perc, i):
    """Test `exchange` against vyper implementation."""
    j = 1 - i

    pool = initialize_pool(vyper_cryptopool)
    dx = pool.balances[i] * dx_perc // 100

    expected_dy = vyper_cryptopool.exchange(i, j, dx, 0)
    dy, _ = pool.exchange(i, j, dx)

    assert dy == expected_dy

    expected_balances = [vyper_cryptopool.balances(i) for i in range(2)]
    assert pool.balances == expected_balances


@given(positive_balance, positive_balance)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_add_liquidity(vyper_cryptopool, x0, x1):
    """Test `add_liquidity` against vyper implementation."""
    assume(0.02 < x0 / x1 < 50)
    xp = [x0, x1]

    precisions = vyper_cryptopool.eval("self._get_precisions()")
    price_scale = vyper_cryptopool.price_scale()
    amounts = get_real_balances(xp, precisions, price_scale)

    pool = initialize_pool(vyper_cryptopool)

    expected_lp_amount = vyper_cryptopool.add_liquidity(amounts, 0)
    # cryptopool.vy doesn't claim admin fees like this, but pool does the claim like
    # tricrypto_ng.vy does for maintainability.
    vyper_cryptopool.claim_admin_fees()
    expected_balances = [vyper_cryptopool.balances(i) for i in range(len(xp))]
    expected_lp_supply = vyper_cryptopool.totalSupply()
    expected_D = vyper_cryptopool.D()

    lp_amount = pool.add_liquidity(amounts)

    assert lp_amount == expected_lp_amount
    assert pool.balances == expected_balances
    assert pool.tokens == expected_lp_supply
    assert pool.D == expected_D


@given(positive_balance)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_remove_liquidity(vyper_cryptopool, amount):
    """Test `remove_liquidity` against vyper implementation."""
    assume(amount < vyper_cryptopool.totalSupply())

    pool = initialize_pool(vyper_cryptopool)

    # cryptopool.vy doesn't claim admin fees like this, but pool does the claim like
    # tricrypto_ng.vy does for maintainability.
    vyper_cryptopool.claim_admin_fees()
    vyper_cryptopool.remove_liquidity(amount, [0, 0])
    expected_balances = [vyper_cryptopool.balances(i) for i in range(2)]
    expected_lp_supply = vyper_cryptopool.totalSupply()
    expected_D = vyper_cryptopool.D()

    pool.remove_liquidity(amount)

    assert pool.balances == expected_balances
    assert pool.tokens == expected_lp_supply
    assert pool.D == expected_D


@given(positive_balance, st.integers(min_value=0, max_value=1))
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_remove_liquidity_one_coin(vyper_cryptopool, amount, i):
    """Test `remove_liquidity_one_coin` against vyper implementation."""
    assume(amount < vyper_cryptopool.totalSupply())

    pool = initialize_pool(vyper_cryptopool)

    # cryptopool.vy doesn't claim admin fees like this, but pool does the claim like
    # tricrypto_ng.vy does for maintainability.
    vyper_cryptopool.claim_admin_fees()
    vyper_cryptopool.remove_liquidity_one_coin(amount, i, 0)
    expected_coin_balance = vyper_cryptopool.balances(i)
    expected_lp_supply = vyper_cryptopool.totalSupply()

    pool.remove_liquidity_one_coin(amount, i, 0)
    coin_balance = pool.balances[i]
    lp_supply = pool.tokens

    assert coin_balance == expected_coin_balance
    assert lp_supply == expected_lp_supply


@given(positive_balance, st.integers(min_value=0, max_value=1))
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=25,
    deadline=None,
)
def test_calc_withdraw_one_coin(vyper_cryptopool, amount, i):
    """Test `calc_withdraw_one_coin` against vyper implementation."""
    assume(amount < vyper_cryptopool.totalSupply())

    n_coins = 2

    pool = initialize_pool(vyper_cryptopool)

    expected_dy = vyper_cryptopool.calc_withdraw_one_coin(amount, i)
    dy = pool.calc_withdraw_one_coin(amount, i)
    assert dy == expected_dy

    expected_balances = [vyper_cryptopool.balances(i) for i in range(n_coins)]
    assert pool.balances == expected_balances


@given(price, price, st.integers(min_value=0, max_value=1000))
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_price_oracle(vyper_cryptopool, price_oracle, last_price, time_delta):
    """Test `price_oracle` and `lp_price` against vyper implementation."""
    vyper_cryptopool.eval(f"self._price_oracle={price_oracle}")
    vyper_cryptopool.eval(f"self.last_prices={last_price}")
    vm_timestamp = boa.env.vm.state.timestamp
    last_prices_timestamp = vm_timestamp - time_delta
    vyper_cryptopool.eval(f"self.last_prices_timestamp={last_prices_timestamp}")

    pool = initialize_pool(vyper_cryptopool)
    # pylint: disable-next=protected-access
    pool._increment_timestamp(timestamp=vm_timestamp)

    assert pool.price_oracle() == [vyper_cryptopool.price_oracle()]
    assert pool.lp_price() == vyper_cryptopool.lp_price()


@given(positive_balance, positive_balance, price)
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_get_virtual_price(
    vyper_cryptopool, cryptopool_lp_token, D, tokens, price_scale
):
    vyper_cryptopool.eval(f"self.D={D}")
    cryptopool_lp_token.eval(f"self.totalSupply={tokens}")
    vyper_cryptopool.eval(f"self.price_scale={price_scale}")
    pool = initialize_pool(vyper_cryptopool)

    expected_virtual_price = vyper_cryptopool.get_virtual_price()
    virtual_price = pool.get_virtual_price()
    assert virtual_price == expected_virtual_price


@given(bps_change, bps_change)
@settings(
    suppress_health_check=[
        HealthCheck.function_scoped_fixture,
        HealthCheck.filter_too_much,
    ],
    max_examples=5,
    deadline=None,
)
def test_calc_token_amount(vyper_cryptopool, x0_perc, x1_perc):
    """Test `calc_token_amount` against vyper implementation."""
    n_coins = 2
    percents = [x0_perc, x1_perc]

    assume(not (x0_perc == 0 and x1_perc == 0))

    amountsp = [
        percent * xp // 10000
        for percent, xp in zip(percents, vyper_cryptopool.internal.xp())
    ]

    precisions = vyper_cryptopool.eval("self._get_precisions()")
    price_scale = vyper_cryptopool.price_scale()
    amounts = get_real_balances(amountsp, precisions, price_scale)

    pool = initialize_pool(vyper_cryptopool)

    expected_lp_amount = vyper_cryptopool.calc_token_amount(amounts)
    lp_amount = pool.calc_token_amount(amounts)
    assert lp_amount == expected_lp_amount

    expected_balances = [vyper_cryptopool.balances(i) for i in range(n_coins)]
    assert pool.balances == expected_balances


_num_iter = 10


@given(
    st.lists(
        st.integers(min_value=1, max_value=5000),
        min_size=_num_iter,
        max_size=_num_iter,
    ),
    st.lists(
        st.tuples(
            st.integers(min_value=0, max_value=1),
            st.integers(min_value=0, max_value=1),
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
    vyper_cryptopool, dx_perc_list, indices_list, time_delta_list
):
    """Test `exchange` against vyper implementation."""

    pool = initialize_pool(vyper_cryptopool)

    for indices, dx_perc, time_delta in zip(
        indices_list, dx_perc_list, time_delta_list
    ):
        vm_timestamp = boa.env.vm.state.timestamp
        pool._block_timestamp = vm_timestamp

        i, j = indices
        dx = pool.balances[i] * dx_perc // 10000  # dx_perc in bps

        expected_dy = vyper_cryptopool.exchange(i, j, dx, 0)
        dy, _ = pool.exchange(i, j, dx)
        assert dy == expected_dy

        expected_balances = [vyper_cryptopool.balances(i) for i in range(2)]
        assert pool.balances[0] == expected_balances[0]
        assert pool.balances[1] == expected_balances[1]

        assert pool.last_prices == [vyper_cryptopool.last_prices()]
        assert pool.last_prices_timestamp == vyper_cryptopool.last_prices_timestamp()

        expected_price_oracle = [vyper_cryptopool.price_oracle()]
        expected_price_scale = [vyper_cryptopool.price_scale()]
        assert pool.price_oracle() == expected_price_oracle
        assert pool.price_scale == expected_price_scale

        boa.env.time_travel(time_delta)


def test_dydxfee(vyper_cryptopool):
    """Test spot price formula against execution price for small trades."""
    pool = initialize_pool(vyper_cryptopool)

    # STG, USDC
    decimals = [18, 6]
    precisions = [10 ** (18 - d) for d in decimals]

    i = 0
    j = 1
    dx = 10**18

    dydx = pool.dydxfee(i, j)
    dy = vyper_cryptopool.exchange(i, j, dx, 0)

    dx *= precisions[i]
    dy *= precisions[j]
    assert abs(dydx - dy / dx) < 1e-6


def test_claim_admin_fees(vyper_cryptopool):
    """Test admin fee claim against vyper implementation."""
    update_cached_values(vyper_cryptopool)
    pool = initialize_pool(vyper_cryptopool)

    # vyper_cryptopool's xcp_profit starts out > xcp_profit_a
    actual_xcp_profit = pool.xcp_profit
    xcp_profit_a = pool.xcp_profit_a
    D = pool.D
    tokens = pool.tokens
    vprice = pool.virtual_price

    reduced_xcp_profit = pool.xcp_profit_a - 1
    vyper_cryptopool.eval(f"self.xcp_profit = {reduced_xcp_profit}")
    pool.xcp_profit = reduced_xcp_profit

    vyper_cryptopool.claim_admin_fees()
    pool._claim_admin_fees()

    # shouldn't have enough profit to claim admin fees
    assert (
        pool.xcp_profit <= pool.xcp_profit_a
        and vyper_cryptopool.xcp_profit() <= vyper_cryptopool.xcp_profit_a()
    )
    assert D == pool.D == vyper_cryptopool.D()
    assert tokens == pool.tokens == vyper_cryptopool.totalSupply()
    assert reduced_xcp_profit == pool.xcp_profit == vyper_cryptopool.xcp_profit()
    assert xcp_profit_a == pool.xcp_profit_a == vyper_cryptopool.xcp_profit_a()
    assert vprice == pool.virtual_price == vyper_cryptopool.get_virtual_price()

    vyper_cryptopool.eval(f"self.xcp_profit = {actual_xcp_profit}")
    pool.xcp_profit = actual_xcp_profit

    # should have enough profit to claim admin fees
    assert (
        pool.xcp_profit > pool.xcp_profit_a
        and vyper_cryptopool.xcp_profit() > vyper_cryptopool.xcp_profit_a()
    )

    expected_fees = (
        (pool.xcp_profit - pool.xcp_profit_a) * pool.admin_fee // (2 * 10**10)
    )
    expected_token_frac = vprice * 10**18 // (vprice - expected_fees) - 10**18
    expected_token_supply = pool.tokens + (
        pool.tokens * expected_token_frac // 10**18
    )

    expected_xcp_profit = pool.xcp_profit - expected_fees * 2
    expected_vprice = 10**18 * pool._get_xcp(pool.D) // expected_token_supply

    vyper_cryptopool.claim_admin_fees()
    pool._claim_admin_fees()

    assert D == pool.D == vyper_cryptopool.D()  # D shouldn't change
    assert expected_token_supply == pool.tokens == vyper_cryptopool.totalSupply()
    assert expected_xcp_profit == pool.xcp_profit == vyper_cryptopool.xcp_profit()
    assert expected_xcp_profit == pool.xcp_profit_a == vyper_cryptopool.xcp_profit_a()
    assert expected_vprice == pool.virtual_price == vyper_cryptopool.get_virtual_price()
