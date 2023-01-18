from itertools import combinations

import pytest

from curvesim.pipelines.arbitrage import Arbitrageur
from curvesim.pool.sim_interface.simpool import SimStableswapBase
from curvesim.utils import override

# pylint: disable=redefined-outer-name


class FakeSimStableswap(SimStableswapBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.n = 3

        # used for stubbing private methods
        self._prices = [1.01, 0.98, 1.02, 1.003]
        self._xp = [529818 * 10**18, 760033 * 10**18, 434901 * 10**18]

    @property
    @override
    def _base_index_combos(self):
        return combinations(range(self.n), 2)

    @override
    def _init_coin_indices(self):
        return {"SYM_0": 0, "SYM_1": 1, "SYM_2": 2}

    @override
    def _test_trade(self, coin_in, coin_out, factor):
        return

    @override
    def make_error_fns(self):
        all_idx = range(self.n)
        index_combos = combinations(all_idx, 2)
        xp = self._xp

        def get_trade_bounds(i, j):
            high = xp[i]
            return (0, high)

        def post_trade_price_error(dx, i, j, price_target):
            return 0.0000000123

        def post_trade_price_error_multi(dxs, price_targets, coins):
            errors = [0.00000001] * len(dxs)
            return errors

        return (
            get_trade_bounds,
            post_trade_price_error,
            post_trade_price_error_multi,
            index_combos,
        )

    @override
    def price(self, coin_in, coin_out, use_fee=True):
        return self._prices[0]

    @override
    def trade(self, coin_in, coin_out, size):
        out_amount = size
        fee = 0
        volume = 0
        return out_amount, fee, volume


@pytest.fixture(scope="function")
def sim_stableswap():
    """Fixture for testing derived class"""
    return FakeSimStableswap()


def test_sim_stableswap_init(sim_stableswap):
    """Test __init__"""
    assert sim_stableswap.n == 3


def test_sim_stableswap_coin_indices(sim_stableswap):
    """Test index conversion and getting"""
    result = sim_stableswap.get_coin_indices("SYM_2", "SYM_0")
    assert result == [2, 0]

    result = sim_stableswap.get_coin_indices(1, 2)
    assert result == [1, 2]


def test_trade(sim_stableswap):
    trader = Arbitrageur(sim_stableswap)
    prices = [1] * sim_stableswap.n
    volume_limits = [100000] * sim_stableswap.n
    trades, _, _ = trader.compute_trades(prices, volume_limits)
    print(trades)


def test_price_depth(sim_stableswap):
    ...
