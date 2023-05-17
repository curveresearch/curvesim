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

    @override
    def _init_coin_indices(self):
        return {"SYM_0": 0, "SYM_1": 1, "SYM_2": 2}

    @override
    def test_trade(self, coin_in, coin_out, factor):
        pre_price = self.price(coin_in, coin_out)
        # post_price should be less than pre_price
        post_price = 0.90 * pre_price
        return post_price

    @override
    def make_error_fns(self):
        all_idx = range(self.n)
        index_combos = combinations(all_idx, 2)

        # pylint: disable=unused-argument

        def get_trade_bounds(i, j):
            xp = [529818 * 10**18, 760033 * 10**18, 434901 * 10**18]
            high = xp[i]
            return (0, high)

        def post_trade_price_error(dx, i, j, price_target):
            price = self.price(i, j)

            # solver requires opposite signs for the value
            # of the error function on the bounds
            lo, hi = get_trade_bounds(i, j)
            if abs(dx - lo) < 0.000000005:  # pylint: disable=no-else-return
                price = 2
                return price - price_target
            elif abs(dx - hi) < 0.000000005:
                price = 0
                return price - price_target
            else:
                return 0.00000001

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
        _prices = {
            (0, 1): 1.0002,
            (0, 2): 0.99821,
            (1, 2): 0.989199,
        }
        for (i, j), p in _prices.copy().items():
            _prices[(j, i)] = 1 / p
        return _prices[(coin_in, coin_out)]

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
    prices = [1.00, 1.01, 0.98]
    volume_limits = [100000, 125000, 150000]
    trades, _, _ = trader.compute_trades(prices, volume_limits)
    assert len(trades) == 3
    for t in trades:
        _, _, size = t
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
