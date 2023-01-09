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
