"""Unit tests for SimStableswapBase"""
import pytest

from curvesim.pool.sim_interface.asset_indices import AssetIndicesMixin
from curvesim.utils import override

# pylint: disable=redefined-outer-name


class FakeSimPool(AssetIndicesMixin):
    """
    Fake implementation of a subclass of `CoinIndicesMixin`
    for testing purposes.
    """

    @property
    @override
    def asset_names(self):
        return ["SYM_0", "SYM_1", "SYM_2"]

    @property
    @override
    def _asset_balances(self):
        return [100, 200, 300]


@pytest.fixture(scope="function")
def sim_pool():
    """Fixture for testing derived class"""
    return FakeSimPool()


def test_asset_indices(sim_pool):
    """Test index conversion and getting"""
    result = sim_pool.get_asset_indices("SYM_2", "SYM_0")
    assert result == [2, 0]

    result = sim_pool.get_asset_indices(1, 2)
    assert result == [1, 2]

    assert sim_pool.asset_indices == {"SYM_0": 0, "SYM_1": 1, "SYM_2": 2}

    assert sim_pool.asset_balances == {"SYM_0": 100, "SYM_1": 200, "SYM_2": 300}
