"""Unit tests for SimStableswapBase"""
from itertools import combinations

import pytest

from curvesim.pipelines.arbitrage import Arbitrageur
from curvesim.pool.sim_interface.simpool import SimStableswapBase
from curvesim.utils import override

# pylint: disable=redefined-outer-name


class FakeSimStableswap(SimStableswapBase):
    """
    Fake implementation of a subclass of `SimStableswapBase`
    for testing purposes.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.n = 3

        # used for stubbing private methods
        self._prices = [
            1.01,
            0.98,
            1.003,
            1.00002,
            0.99992,
            1.0000000001,
            1.00000000000000000000001,
        ]
        self._price_counter = 0
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
        pre_price = self.price(coin_in, coin_out)
        # post_price should be less than pre_price
        post_price = 0.90 * pre_price
        return post_price

    @override
    def make_error_fns(self):
        all_idx = range(self.n)
        index_combos = combinations(all_idx, 2)
        xp = self._xp

        # pylint: disable=unused-argument

        def get_trade_bounds(i, j):
            high = xp[i]
            return (0, high)

        def post_trade_price_error(dx, i, j, price_target):
            price = self.price(i, j)
            return price - price_target

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
        prices = self._prices
        counter = self._price_counter

        price = prices[counter]
        self._price_counter = (counter + 1) % len(prices)

        return price

    @override
    def trade(self, coin_in, coin_out, size):
        out_amount = size
        fee = 0
        volume = 10**18
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


def test_compute_trades(sim_stableswap):
    """Test error functions with Arbitrageur.compute_trades"""
    trader = Arbitrageur(sim_stableswap)
    prices = [1] * sim_stableswap.n
    volume_limits = [100000] * sim_stableswap.n
    trades, _, _ = trader.compute_trades(prices, volume_limits)
    assert len(trades) == 3
    for t in trades:
        size = t[2]
        assert size > 0


def test_do_trades(sim_stableswap):
    """Test trade method with Arbitrageur.do_trades"""
    trader = Arbitrageur(sim_stableswap)
    trades = []
    trades_done, volume = trader.do_trades(trades)
    assert trades_done == []  # pylint: disable=use-implicit-booleaness-not-comparison
    assert volume == 0

    trades = [
        (0, 1, 99999999990000015900672),
        (2, 0, 86980634902377172828160),
        (2, 1, 86980634902377172828160),
    ]
    trades_done, volume = trader.do_trades(trades)
    # volume is faked to produce 1 * 10**18 each trade
    assert volume == len(trades) * 10**18
    for t in trades_done:
        # `trade` is faked to produce out amount equal to in amount
        assert t[2] == t[3]


def test_price_depth(sim_stableswap):
    price_depth = sim_stableswap.get_price_depth()
    assert len(price_depth) == 3
    for d in price_depth:
        assert d > 0