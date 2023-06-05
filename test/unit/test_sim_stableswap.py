"""Unit tests for SimStableswapBase"""
import pytest

from curvesim.pipelines.vol_limited_arb.trader import VolumeLimitedArbitrageur
from curvesim.pool.sim_interface.simpool import SimStableswapBase
from curvesim.pool.snapshot import CurvePoolBalanceSnapshot, SnapshotMixin
from curvesim.utils import override

# pylint: disable=redefined-outer-name


# def post_trade_price_error(dx, i, j, price_target):
#     price = pool.price(i, j)
#
#     # solver requires opposite signs for the value
#     # of the error function on the bounds
#     lo, hi = get_trade_bounds(i, j)
#     if abs(dx - lo) < 0.000000005:  # pylint: disable=no-else-return
#         price = 2
#         return price - price_target
#     elif abs(dx - hi) < 0.000000005:
#         price = 0
#         return price - price_target
#     else:
#         return 0.00000001


def post_trade_price_error_multi(dxs, price_targets, coins):
    errors = [0.00000001] * len(dxs)
    return errors


def make_error_fns(pool):
    def get_trade_bounds(i, j):
        high = pool.balances[i]
        return (0, high)

    return get_trade_bounds


class FakeSimStableswap(SimStableswapBase, SnapshotMixin):
    """
    Fake implementation of a subclass of `SimStableswapBase`
    for testing purposes.
    """

    snapshot_class = CurvePoolBalanceSnapshot

    def __init__(self, *args, **kwargs):
        # setup the pool attributes before initializing `SimStableSwapBase`
        self.n_total = 3
        self.balances = [529818 * 10**18, 760033 * 10**18, 434901 * 10**18]
        self.admin_balances = [0, 0, 0]
        self.rates = [10**18] * 3

        super().__init__(*args, **kwargs)

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

    @override
    def get_in_amount(self, coin_in, coin_out, out_balance_perc):
        return 0


# pool_type_to_error_functions[FakeSimStableswap] = make_error_fns


@pytest.fixture(scope="function")
def sim_stableswap():
    """Fixture for testing derived class"""
    return FakeSimStableswap()


def test_number_of_coins(sim_stableswap):
    """Test `number_of_coins`"""
    assert sim_stableswap.number_of_coins == 3


def test_sim_stableswap_coin_indices(sim_stableswap):
    """Test index conversion and getting"""
    result = sim_stableswap.get_coin_indices("SYM_2", "SYM_0")
    assert result == [2, 0]

    result = sim_stableswap.get_coin_indices(1, 2)
    assert result == [1, 2]


@pytest.mark.skip(reason="wip")
def test_compute_trades(sim_stableswap):
    """Test error functions with Arbitrageur.compute_trades"""
    trader = VolumeLimitedArbitrageur(sim_stableswap)
    prices = [1.00, 1.01, 0.98]
    volume_limits = [100000, 125000, 150000]
    trades, _, _ = trader.compute_trades(prices, volume_limits)
    assert len(trades) == 3
    for t in trades:
        _, _, size = t
        assert size > 0


@pytest.mark.skip(reason="wip")
def test_do_trades(sim_stableswap):
    """Test trade method with Arbitrageur.do_trades"""
    trader = VolumeLimitedArbitrageur(sim_stableswap)
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
