"""
Unit tests for CurveCryptoPool for n = 3

Tests are against the tricrypto-ng contract.
"""
import os

import boa
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from curvesim.pool import CurveCryptoPool
from curvesim.pool.cryptoswap.pool import A_MULTIPLIER, MAX_GAMMA, MIN_GAMMA, PRECISION

N_COINS = 3
MIN_A = N_COINS**N_COINS * A_MULTIPLIER // 10
MAX_A = N_COINS**N_COINS * A_MULTIPLIER * 100000


def get_math(tricrypto):
    _base_dir = os.path.dirname(__file__)
    filepath = os.path.join(_base_dir, "../fixtures/curve/tricrypto_math.vy")
    _math = tricrypto.MATH()
    MATH = boa.load_partial(filepath).at(_math)
    return MATH


def unpack_3_uint64s(packed_nums):
    mask = 2**64 - 1
    return [
        (packed_nums >> 128) & mask,
        (packed_nums >> 64) & mask,
        packed_nums & mask,
    ]


def pack_3_uint64s(nums):
    return (nums[0] << 128) | (nums[1] << 64) | nums[0]


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

    price_scale = [vyper_tricrypto.price_scale(i) for i in range(2)]
    balances = [vyper_tricrypto.balances(i) for i in range(n_coins)]
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
        balances=balances,
        D=D,
        tokens=lp_total_supply,
        xcp_profit=xcp_profit,
        xcp_profit_a=xcp_profit_a,
    )

    assert pool.A == vyper_tricrypto.A()
    assert pool.gamma == vyper_tricrypto.gamma()
    assert pool.balances == balances
    assert pool.D == vyper_tricrypto.D()
    assert pool.tokens == lp_total_supply
    assert pool.xcp_profit == xcp_profit
    assert pool.xcp_profit_a == xcp_profit_a

    virtual_price = vyper_tricrypto.virtual_price()
    pool.virtual_price = virtual_price

    price_oracle = [vyper_tricrypto.price_oracle(i) for i in range(2)]
    # pylint: disable-next=protected-access
    pool._price_oracle = price_oracle

    last_prices = [vyper_tricrypto.last_prices(i) for i in range(2)]
    last_prices_timestamp = vyper_tricrypto.last_prices_timestamp()

    pool.last_prices = last_prices
    pool.last_prices_timestamp = last_prices_timestamp

    return pool


def sync_ema_logic(
    vyper_tricrypto,
    pool,
    last_prices,
):
    """
    Test helper to synchronize state variables needed for EMA update.

    This is needed because the local evm block timestamp will drift
    from the python pool's internal timestamp.
    """
    # pylint: disable=protected-access
    price_oracle = vyper_tricrypto.eval("self._price_oracle")
    pool._price_oracle = [price_oracle]

    # synchronize the times between the two pools and reset
    # last_prices and last_prices_timestamp
    vyper_tricrypto.eval(f"self.last_prices={last_prices}")
    pool.last_prices = [last_prices]

    vm_timestamp = boa.env.vm.state.timestamp
    pool._increment_timestamp(timestamp=vm_timestamp)

    last_prices_timestamp = vm_timestamp - 120
    vyper_tricrypto.eval(f"self.last_prices_timestamp={last_prices_timestamp}")
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
    max_examples=10,
    deadline=None,
)
def test_exchange(vyper_tricrypto, dx_perc, i, j):
    """Test `exchange` against vyper implementation."""
    assume(i != j)

    tols = [1, 1, 1e9]

    pool = initialize_pool(vyper_tricrypto)
    dx = pool.balances[i] * dx_perc // 100

    expected_dy = vyper_tricrypto.exchange(i, j, dx, 0)
    dy, _ = pool.exchange(i, j, dx)
    # assert dy == expected_dy
    assert abs(dy - expected_dy) < tols[j]

    expected_balances = [vyper_tricrypto.balances(i) for i in range(3)]
    # assert pool.balances == expected_balances
    assert abs(pool.balances[0] - expected_balances[0]) < tols[0]
    assert abs(pool.balances[1] - expected_balances[1]) < tols[1]
    assert abs(pool.balances[2] - expected_balances[2]) < tols[2]
