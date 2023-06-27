"""Unit tests for SimStableswapBase"""
import pytest

from curvesim.pool.sim_interface.coin_indices import CoinIndicesMixin
from curvesim.utils import override

# pylint: disable=redefined-outer-name


class FakeSimPool(CoinIndicesMixin):
    """
    Fake implementation of a subclass of `CoinIndicesMixin`
    for testing purposes.
    """

    @property
    @override
    def coin_indices(self):
        return {"SYM_0": 0, "SYM_1": 1, "SYM_2": 2}


@pytest.fixture(scope="function")
def sim_pool():
    """Fixture for testing derived class"""
    return FakeSimPool()


def test_coin_indices(sim_pool):
    """Test index conversion and getting"""
    result = sim_pool.get_coin_indices("SYM_2", "SYM_0")
    assert result == [2, 0]

    result = sim_pool.get_coin_indices(1, 2)
    assert result == [1, 2]
