"""Unit tests for the SnapshotMixin and derived subclasses of Snapshot."""
import pytest

from curvesim.exceptions import SnapshotError
from curvesim.pool.sim_interface import SimCurveMetaPool, SimCurvePool
from curvesim.pool.snapshot import SnapshotMixin


def test_snapshot_raises_exception():
    """Test error thrown for missing snapshot class."""
    obj = SnapshotMixin()
    with pytest.raises(SnapshotError):
        obj.get_snapshot()


def test_pool_balance_snapshot():
    """Test balances are copied and reset properly for SimCurvePool."""
    pool = SimCurvePool(A=250, D=1000000 * 10**18, n=2, admin_fee=5 * 10**9)

    snapshot = pool.get_snapshot()

    pre_balances = pool.balances.copy()
    pre_admin_balances = pool.admin_balances.copy()
    pool.exchange(0, 1, 10**12)
    post_balances = pool.balances.copy()
    post_admin_balances = pool.admin_balances.copy()
    assert pre_balances != post_balances
    assert pre_admin_balances != post_admin_balances

    pool.revert_to_snapshot(snapshot)
    assert pool.balances == pre_balances
    assert pool.admin_balances == pre_admin_balances


def test_metapool_balance_snapshot():
    """Test balances are copied and reset properly for SimCurveMetaPool."""
    basepool = SimCurvePool(A=1000, D=2750000 * 10**18, n=2, admin_fee=5 * 10**9)
    pool = SimCurveMetaPool(
        A=250, D=4000000 * 10**18, n=2, admin_fee=5 * 10**9, basepool=basepool
    )

    snapshot = pool.get_snapshot()

    pre_balances = pool.balances.copy()
    pre_bp_balances = basepool.balances.copy()
    pre_admin_balances = pool.admin_balances.copy()
    pre_bp_admin_balances = basepool.admin_balances.copy()
    pre_lp_tokens = basepool.tokens

    # ---- test top-level exchange ---- #

    pool.exchange(0, 1, 10**12)

    # `exchange` changes values for metapool not basepool
    assert pool.balances != pre_balances
    assert pool.admin_balances != pre_admin_balances
    assert basepool.balances == pre_bp_balances
    assert basepool.admin_balances == pre_bp_admin_balances
    assert basepool.tokens == pre_lp_tokens

    pool.revert_to_snapshot(snapshot)

    assert pool.balances == pre_balances
    assert pool.admin_balances == pre_admin_balances
    assert basepool.balances == pre_bp_balances
    assert basepool.admin_balances == pre_bp_admin_balances

    # -- test exchange between primary and basepool underlyer -- #

    pool.exchange_underlying(0, 1, 157 * 10**18)

    # `exchange_underlying` should change basepool values
    assert pool.balances != pre_balances
    assert pool.admin_balances != pre_admin_balances
    assert basepool.balances != pre_bp_balances
    assert basepool.admin_balances != pre_bp_admin_balances
    assert basepool.tokens != pre_lp_tokens

    pool.revert_to_snapshot(snapshot)

    assert pool.balances == pre_balances
    assert pool.admin_balances == pre_admin_balances
    assert basepool.balances == pre_bp_balances
    assert basepool.admin_balances == pre_bp_admin_balances
    assert basepool.tokens == pre_lp_tokens


def test_2_coin_cryptopool_balance_snapshot(sim_curve_crypto_pool):
    _test_cryptool_balance_snapshot(sim_curve_crypto_pool)


def test_tricrypto_balance_snapshot(sim_curve_tricrypto_pool):
    _test_cryptool_balance_snapshot(sim_curve_tricrypto_pool)


def _test_cryptool_balance_snapshot(pool):
    snapshot = pool.get_snapshot()

    pre_balances = pool.balances.copy()
    pre_D = pool.D
    pre_price_scale = pool.price_scale.copy()
    pre_price_oracle = pool._price_oracle.copy()
    pre_virtual_price = pool.virtual_price
    pre_xcp_profit = pool.xcp_profit
    pre_xcp_profit_a = pool.xcp_profit_a
    pre_last_prices = pool.last_prices.copy()
    pre_last_prices_timestamp = pool.last_prices_timestamp

    # ---- test exchange ---- #
    # Use two trades since last_prices == _price_oracle at start
    pool._increment_timestamp(42)  # 504 seconds
    pool.exchange(0, 1, 10**26 // 2)
    pool._increment_timestamp(42)
    pool.exchange(0, 1, 10**26 // 2)

    # test that `exchange` changes expected values
    assert pool.balances != pre_balances
    assert pool.D != pre_D
    assert pool.price_scale != pre_price_scale  # _tweak_price should update price_scale
    assert pool._price_oracle != pre_price_oracle
    assert pool.virtual_price != pre_virtual_price
    assert pool.xcp_profit != pre_xcp_profit
    assert pool.xcp_profit_a == pre_xcp_profit_a  # not claimed yet
    assert pool.last_prices != pre_last_prices
    assert pool.last_prices_timestamp != pre_last_prices_timestamp

    # test _claim_admin_fees
    pool._claim_admin_fees()
    assert pool.xcp_profit_a != pre_xcp_profit_a

    # Ensure all reverted
    pool.revert_to_snapshot(snapshot)
    assert pool.balances == pre_balances
    assert pool.D == pre_D
    assert pool.price_scale == pre_price_scale
    assert pool._price_oracle == pre_price_oracle
    assert pool.virtual_price == pre_virtual_price
    assert pool.xcp_profit == pre_xcp_profit
    assert pool.xcp_profit_a == pre_xcp_profit_a
    assert pool.last_prices == pre_last_prices
    assert pool.last_prices_timestamp == pre_last_prices_timestamp


def test_snapshot_context():
    """Test context manager."""
    pool = SimCurvePool(A=250, D=1000000 * 10**18, n=2, admin_fee=5 * 10**9)

    pre_balances = pool.balances.copy()
    pre_admin_balances = pool.admin_balances.copy()

    with pool.use_snapshot_context():
        pool.exchange(0, 1, 10**12)
        assert pool.balances != pre_balances
        assert pool.admin_balances != pre_admin_balances

    assert pool.balances == pre_balances
    assert pool.admin_balances == pre_admin_balances
