from abc import ABC, abstractmethod
from contextlib import contextmanager

from curvesim.exceptions import SnapshotError


class SnapshotMixin:
    """
    Pool mixin to allow ability to snapshot partial states
    and revert back to it.

    Main class must have `snapshot_class` attribute, which
    implements the `Snapshot` interface.
    """

    snapshot_class = None

    def get_snapshot(self):
        """Saves the pool's partial state."""
        if not self.snapshot_class:
            raise SnapshotError("Snapshot class is not set.")

        snapshot = self.snapshot_class.create(self)
        return snapshot

    def revert_to_snapshot(self, snapshot):
        """
        Reverts state to the given partial state.

        Parameters
        -----------
        snapshot: Snapshot
            The saved data from a prior pool state.
        """
        snapshot.restore(self)

    @contextmanager
    def use_snapshot_context(self):
        """
        This context manager allows creating and reverting
        to snapshots easily with the syntax:

        with pool.use_snapshot_context() as snapshot:
            pool.trade(i, j, dx)
            ...
            etc.

        The pool state will be reverted after the `with` block
        to the state prior to the block.

        `as snapshot` can be omitted but is handy if you need to
        log or introspect on the state.
        """
        snapshot = self.get_snapshot()
        try:
            yield snapshot
        finally:
            self.revert_to_snapshot(snapshot)


class Snapshot(ABC):
    """
    This class allows customization of snapshot logic, i.e.
    controls how partial states are produced and restored.
    """

    @classmethod
    @abstractmethod
    def create(cls, pool):
        """
        Create a snapshot of the pool's state.

        Parameters
        -----------
        pool: object
            The object whose state we are saving as a snapshot.

        Returns
        -------
        Snapshot
            The saved data from the pool state.
        """
        raise NotImplementedError

    @abstractmethod
    def restore(self, pool):
        """
        Update the pool's state using the snapshot data.

        Parameters
        -----------
        pool: object
            The object whose state we have saved as a snapshot.
        """
        raise NotImplementedError


class CurvePoolBalanceSnapshot(Snapshot):
    """Snapshot that saves pool balances and admin balances."""

    def __init__(self, balances, admin_balances):
        self.balances = balances
        self.admin_balances = admin_balances

    @classmethod
    def create(cls, pool):
        balances = pool.balances.copy()
        admin_balances = pool.admin_balances.copy()
        return cls(balances, admin_balances)

    def restore(self, pool):
        pool.balances = self.balances.copy()
        pool.admin_balances = self.admin_balances.copy()


class CurveMetaPoolBalanceSnapshot(Snapshot):
    """
    Snapshot that saves pool balances and admin balances
    and also the basepool balances and LP total supply.
    """

    def __init__(
        self, balances, admin_balances, bp_balances, bp_admin_balances, bp_tokens
    ):
        self.balances = balances
        self.admin_balances = admin_balances
        self.bp_balances = bp_balances
        self.bp_admin_balances = bp_admin_balances
        self.bp_tokens = bp_tokens

    @classmethod
    def create(cls, pool):
        balances = pool.balances.copy()
        admin_balances = pool.admin_balances.copy()
        basepool = pool.basepool
        bp_balances = basepool.balances.copy()
        bp_admin_balances = basepool.admin_balances.copy()
        bp_tokens = basepool.tokens
        return cls(balances, admin_balances, bp_balances, bp_admin_balances, bp_tokens)

    def restore(self, pool):
        pool.balances = self.balances.copy()
        pool.admin_balances = self.admin_balances.copy()
        basepool = pool.basepool
        basepool.balances = self.bp_balances.copy()
        basepool.admin_balances = self.bp_admin_balances.copy()
        basepool.tokens = self.bp_tokens
