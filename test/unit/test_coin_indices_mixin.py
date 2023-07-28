"""Unit tests for SimStableswapBase"""
import pytest
import itertools

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
    # Example calling by symbol
    result = sim_pool.get_asset_indices("SYM_2", "SYM_0")
    assert result == [2, 0]

    names = sim_pool.asset_names
    name_sets = [
        list(itertools.permutations(names, r=i)) for i in range(1, len(names) + 1)
    ]
    for lst in name_sets:
        for name_set in lst:
            name_set = list(name_set)
            result = sim_pool.get_asset_indices(*name_set)
            assert result == [names.index(symbol) for symbol in name_set]

    # Example calling by index
    result = sim_pool.get_asset_indices(1, 2)
    assert result == [1, 2]

    indices = sim_pool.asset_indices.values()
    index_sets = [
        list(itertools.permutations(indices, r=i)) for i in range(1, len(indices) + 1)
    ]
    for lst in index_sets:
        for index_set in lst:
            index_set = list(index_set)
            result = sim_pool.get_asset_indices(*index_set)
            assert result == index_set

    assert sim_pool.asset_indices == {"SYM_0": 0, "SYM_1": 1, "SYM_2": 2}


def test_asset_balances(sim_pool):
    assert sim_pool.asset_balances == {"SYM_0": 100, "SYM_1": 200, "SYM_2": 300}
