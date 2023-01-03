from abc import ABC, abstractmethod

from curvesim.exceptions import SnapshotError


class SnapshotMixin:
    snapshot_class = None

    def get_snapshot(self):
        if not self.snapshot_class:
            raise SnapshotError("Snapshot class is not set.")

        snapshot = self.snapshot_class.create(self)
        return snapshot

    def revert_to_snapshot(self, snapshot):
        snapshot.restore(self)


class Snapshot(ABC):
    @classmethod
    @abstractmethod
    def create(cls, pool):
        raise NotImplementedError

    @abstractmethod
    def restore(self, pool):
        raise NotImplementedError


class CurvePoolBalanceSnapshot(Snapshot):
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
