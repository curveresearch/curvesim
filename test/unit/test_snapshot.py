import pytest

from curvesim.exceptions import SnapshotError
from curvesim.pool.sim_interface.pool import SimCurvePool
from curvesim.pool.snapshot import SnapshotMixin


def test_snapshot_raises_exception():
    obj = SnapshotMixin()
    with pytest.raises(SnapshotError):
        obj.get_snapshot()


def test_pool_balance_snapshot():
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
