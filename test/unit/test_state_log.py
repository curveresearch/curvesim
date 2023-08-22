import pytest

from curvesim.exceptions import UnregisteredPoolError
from curvesim.metrics.state_log.pool_parameters import get_pool_parameters
from curvesim.metrics.state_log.pool_state import get_pool_state

# To Do: Currently only get_pool_parameters/get_pool_state are tested.


def test_get_pool_parameters_curve_pool(sim_curve_pool):
    """Test that get_pool_parameters returns the right data for SimCurvePool."""
    pool = sim_curve_pool

    expected_params = {
        "A": pool.A,
        "D": pool.D() / 10**18,
        "fee": pool.fee / 10**10,
        "admin_fee": pool.admin_fee / 10**10,
    }

    params = get_pool_parameters(pool)
    assert params == expected_params

    # Test with fee_mul
    pool.fee_mul = 2 * 10**10
    expected_params["fee_mul"] = 2
    params = get_pool_parameters(pool)
    assert params == expected_params


def test_get_pool_parameters_curve_crypto_pool(sim_curve_crypto_pool):
    """Test that get_pool_parameters returns the right data for SimCurveCryptoPool."""
    pool = sim_curve_crypto_pool

    expected_params = {
        "A": pool.A,
        "gamma": pool.gamma / 10**18,
        "D": pool.D / 10**18,
        "mid_fee": pool.mid_fee / 10**10,
        "out_fee": pool.out_fee / 10**10,
        "fee_gamma": pool.fee_gamma / 10**18,
        "allowed_extra_profit": pool.allowed_extra_profit / 10**18,
        "adjustment_step": pool.adjustment_step / 10**18,
        "ma_half_time": pool.ma_half_time,
        "admin_fee": pool.admin_fee / 10**10,
    }

    params = get_pool_parameters(pool)
    assert params == expected_params


def test_get_pool_parameters_curve_meta_pool(sim_curve_meta_pool):
    """Test that get_pool_parameters returns the right data for SimCurveMetaPool."""
    _test_get_pool_parameters_curve_meta_pool(sim_curve_meta_pool)


def test_get_pool_parameters_curve_rai_pool(sim_curve_rai_pool):
    """Test that get_pool_parameters returns the right data for SimCurveRaiPool."""
    _test_get_pool_parameters_curve_meta_pool(sim_curve_rai_pool)


def _test_get_pool_parameters_curve_meta_pool(pool):
    expected_params = {
        "A": pool.A,
        "D": pool.D() / 10**18,
        "fee": pool.fee / 10**10,
        "admin_fee": pool.admin_fee / 10**10,
        "A_base": pool.basepool.A,
        "D_base": pool.basepool.D() / 10**18,
        "fee_base": pool.basepool.fee / 10**10,
        "admin_fee_base": pool.basepool.admin_fee / 10**10,
    }

    params = get_pool_parameters(pool)
    assert params == expected_params

    # Test with fee_mul
    pool.fee_mul = 2 * 10**10
    pool.basepool.fee_mul = 3 * 10**10
    expected_params["fee_mul"] = 2
    expected_params["fee_mul_base"] = 3

    params = get_pool_parameters(pool)
    assert params == expected_params


def test_get_pool_parameters_unmapped_exception():
    """Test that unmapped pool throws error."""

    class DummyPool:
        pass

    pool = DummyPool()

    with pytest.raises(UnregisteredPoolError):
        get_pool_parameters(pool)


def test_get_pool_state_curve_pool(sim_curve_pool):
    """Test that get_pool_state returns the right data for SimCurvePool."""
    pool = sim_curve_pool

    expected_state = {
        "balances": pool.balances,
        "tokens": pool.tokens,
        "admin_balances": pool.admin_balances,
    }

    state = get_pool_state(pool)
    assert state == expected_state


def test_get_pool_state_curve_crypto_pool(sim_curve_crypto_pool):
    """Test that get_pool_state returns the right data for SimCurveCryptoPool."""
    pool = sim_curve_crypto_pool

    expected_state = {
        "D": pool.D,
        "balances": pool.balances,
        "tokens": pool.tokens,
        "price_scale": pool.price_scale,
        "_price_oracle": pool._price_oracle,
        "xcp_profit": pool.xcp_profit,
        "xcp_profit_a": pool.xcp_profit_a,
        "last_prices": pool.last_prices,
        "last_prices_timestamp": pool.last_prices_timestamp,
        "_block_timestamp": pool._block_timestamp,
        "not_adjusted": pool.not_adjusted,
        "virtual_price": pool.virtual_price,
    }

    state = get_pool_state(pool)
    assert state == expected_state


def test_get_pool_state_curve_meta_pool(sim_curve_meta_pool):
    """Test that get_pool_state returns the right data for SimCurveMetaPool."""
    _test_get_pool_state_curve_meta_pool(sim_curve_meta_pool)


def test_get_pool_state_curve_rai_pool(sim_curve_rai_pool):
    """Test that get_pool_state returns the right data for SimCurveRaiPool."""
    _test_get_pool_state_curve_meta_pool(sim_curve_rai_pool)


def _test_get_pool_state_curve_meta_pool(pool):
    expected_state = {
        "balances": pool.balances,
        "tokens": pool.tokens,
        "admin_balances": pool.admin_balances,
        "balances_base": pool.basepool.balances,
        "tokens_base": pool.basepool.tokens,
        "admin_balances_base": pool.basepool.admin_balances,
    }

    state = get_pool_state(pool)
    assert state == expected_state


def test_get_pool_state_unmapped_exception():
    """Test that unmapped pool throws StateLogError."""

    class DummyPool:
        pass

    pool = DummyPool()

    with pytest.raises(UnregisteredPoolError):
        get_pool_state(pool)
