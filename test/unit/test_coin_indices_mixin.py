"""Unit tests for SimStableswapBase"""
import pytest
import itertools

from curvesim.pool.sim_interface.asset_indices import AssetIndicesMixin
from curvesim.exceptions import CurvesimValueError, SimPoolError
from curvesim.utils import override

# pylint: disable=redefined-outer-name


class FakeSimPool(AssetIndicesMixin):
    """
    Fake implementation of a subclass of `CoinIndicesMixin`
    for testing purposes.
    """

    def __init__(self):
        self.asset_names = ["SYM_0", "SYM_1", "SYM_2"]

    @property
    @override
    def asset_names(self):
        return self._asset_names

    @asset_names.setter
    @override
    def asset_names(self, *asset_lists):
        asset_names = asset_lists[0]

        if len(asset_names) != len(set(asset_names)):
            raise SimPoolError("SimPool must have unique asset names.")

        if hasattr(self, "asset_names") and len(self.asset_names) != len(asset_names):
            raise SimPoolError("SimPool must have a consistent number of asset names.")

        if not hasattr(self, "asset_names"):
            self._asset_names = [str()] * len(asset_names)

        for i in range(len(asset_names)):
            self._asset_names[i] = asset_names[i]

    @property
    @override
    def _asset_balances(self):
        return [100, 200, 300]


@pytest.fixture(scope="function")
def sim_pool():
    """Fixture for testing derived class"""
    return FakeSimPool()


def indices(sim_pool, *assets):
    """Returns the indices of all symbols/indices in assets"""
    indices = []
    symbols = sim_pool.asset_names
    for ID in assets:
        if isinstance(ID, str):
            ID = symbols.index(ID)
        indices.append(ID)

    return indices


def duplicates(sim_pool, *assets):
    """Determines whether assets contains duplicate symbols/indices"""
    indices = indices(sim_pool, *assets)

    return len(indices) != len(set(indices))


def test_asset_indices(sim_pool):
    """Test index conversion and getting"""
    assert sim_pool.asset_indices == {"SYM_0": 0, "SYM_1": 1, "SYM_2": 2}


def test_asset_balances(sim_pool):
    """Test mapping symbols to balances"""
    assert sim_pool.asset_balances == {"SYM_0": 100, "SYM_1": 200, "SYM_2": 300}


def test_get_asset_indices(sim_pool):
    """Test getting index from symbol or index itself"""
    # Example calling by symbol
    result = sim_pool.get_asset_indices("SYM_2", "SYM_0")
    assert result == [2, 0]

    # Example calling by index
    result = sim_pool.get_asset_indices(1, 2)
    assert result == [1, 2]

    # Example calling by symbol and index
    result = sim_pool.get_asset_indices("SYM_0", 2, "SYM_1")
    assert result == [0, 2, 1]

    # Examples calling by a symbol that doesn't exist
    try:
        assets = ["SYM_0", 1, "SYM_3"]
        result = sim_pool.get_asset_indices(*assets)
    except Exception as err:
        assert isinstance(err, KeyError)

    try:
        assets = [2, 3, 0]
        result = sim_pool.get_asset_indices(*assets)
    except Exception as err:
        assert isinstance(err, KeyError)

    # Examples calling by symbol and index, with occasional duplicates
    symbols = sim_pool.asset_names
    indices = sim_pool.asset_indices.values()
    symbols_and_indices = symbols + indices
    assets = [
        list(itertools.permutations(symbols_and_indices, r=i))
        for i in range(1, len(symbols_and_indices) + 1)
    ]
    for lst in assets:
        for asset_set in lst:
            try:
                result = sim_pool.get_asset_indices(*asset_set)
                assert result == indices(sim_pool, *asset_set)
            except Exception as err:
                assert duplicates(sim_pool, *asset_set)
                assert isinstance(err, CurvesimValueError)


# test cases where asset_names and asset_balances are unequal length

# setter
# for breaking tests, check that the appropriate exception is raised (may need to use multiple functions in a
# specific order to get the right error)

# non-str input (e.g. ints that are and aren't duplicates of indices of the str)
# change number of symbols after initial set
# initial set that's longer/shorter than _asset_balances
