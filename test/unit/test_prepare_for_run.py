"""Unit tests for SimPool .prepare_for_run method."""

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pandas import DataFrame


def test_cryptoswap2_prepare_for_run_same_price(sim_curve_crypto_pool):
    """Test SimCurveCryptoPool.prepare_for_run with 2-coin pool, no price changes"""
    _test_cryptoswap_prepare_for_run_same_price(sim_curve_crypto_pool)


def test_cryptoswap3_prepare_for_run_same_price(sim_curve_tricrypto_pool):
    """Test SimCurveCryptoPool.prepare_for_run with 3-coin pool, no price changes"""
    _test_cryptoswap_prepare_for_run_same_price(sim_curve_tricrypto_pool)


@given(st.floats(min_value=0.1, max_value=0.9))
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_cryptoswap2_prepare_for_run_low_price(sim_curve_crypto_pool, scalar):
    """Test SimCurveCryptoPool.prepare_for_run with 2-coin pool, lower prices"""
    _test_cryptoswap_prepare_for_run(sim_curve_crypto_pool, scalar)


@given(st.floats(min_value=0.1, max_value=0.9))
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_cryptoswap3_prepare_for_run_low_price(sim_curve_tricrypto_pool, scalar):
    """Test SimCurveCryptoPool.prepare_for_run with 3-coin pool, lower prices"""
    _test_cryptoswap_prepare_for_run(sim_curve_tricrypto_pool, scalar)


@given(st.floats(min_value=1.1, max_value=10))
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_cryptoswap2_prepare_for_run_high_price(sim_curve_crypto_pool, scalar):
    """Test SimCurveCryptoPool.prepare_for_run with 2-coin pool, higher prices"""
    _test_cryptoswap_prepare_for_run(sim_curve_crypto_pool, scalar)


@given(st.floats(min_value=1.1, max_value=10))
@settings(
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    max_examples=5,
    deadline=None,
)
def test_cryptoswap3_prepare_for_run_high_price(sim_curve_tricrypto_pool, scalar):
    """Test SimCurveCryptoPool.prepare_for_run with 3-coin pool, higher prices"""
    _test_cryptoswap_prepare_for_run(sim_curve_tricrypto_pool, scalar)


def _test_cryptoswap_prepare_for_run_same_price(pool):
    """
    Test that preserving price_scale doesn't change D or xcp(D);
    and that virtual_price and xcp_profits are 10**18.
    """
    # pylint: disable=protected-access

    original_D = pool.D
    original_xcp = pool._get_xcp(pool.D)
    original_price_scale = pool.price_scale

    prices = [10**18 / p for p in pool.price_scale]
    prices = DataFrame([prices, prices])

    pool.prepare_for_run(prices)

    # Test that price attributes updated correctly
    _test_list_equality(pool.price_scale, original_price_scale)
    _test_list_equality(pool._price_oracle, original_price_scale)
    _test_list_equality(pool.last_prices, original_price_scale)

    # Test that D/xcp didn't change
    new_xcp = pool._get_xcp(pool.D)

    assert abs(pool.D - original_D) < 10**10
    assert abs(new_xcp - original_xcp) < 10**10

    # Test that virtual price and xcp_profits == 1
    assert pool.virtual_price == 10**18
    assert pool.xcp_profit == 10**18
    assert pool.xcp_profit_a == 10**18


def _test_cryptoswap_prepare_for_run(pool, scalar):
    """
    Test that changing price_scale doesn't change xcp(D), but changes D;
    and that virtual_price and xcp_profits are 10**18.
    """
    # pylint: disable=protected-access
    original_D = pool.D
    original_xcp = pool._get_xcp(pool.D)
    new_price_scale = [int(p * scalar) for p in pool.price_scale]

    prices = [10**18 / p for p in new_price_scale]
    prices = DataFrame([prices, prices])

    pool.prepare_for_run(prices)

    # Test that price attributes updated correctly
    _test_list_equality(pool.price_scale, new_price_scale)
    _test_list_equality(pool._price_oracle, new_price_scale)
    _test_list_equality(pool.last_prices, new_price_scale)

    # Test that xcp didn't change but D did
    new_xcp = pool._get_xcp(pool.D)

    assert abs(pool.D - original_D) > 10**10
    assert abs(new_xcp - original_xcp) < 10**10

    # Test that virtual price and xcp_profits == 1
    assert pool.virtual_price == 10**18
    assert pool.xcp_profit == 10**18
    assert pool.xcp_profit_a == 10**18


def _test_list_equality(list1, list2, tol=10**10):
    """Test that differences are < tol for all elements"""
    assert all(abs(val1 - val2) < tol for val1, val2 in zip(list1, list2))
