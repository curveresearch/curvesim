from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from curvesim.pipelines.vol_limited_arb.trader import _apply_volume_limits
from curvesim.templates.trader import ArbTrade


class DummyPool:
    def __init__(self, min_trade_sizes):
        self.min_trade_sizes = min_trade_sizes

    def get_min_trade_size(self, coin_in):
        return self.min_trade_sizes[coin_in]


random_int = st.integers(min_value=1, max_value=100)
three_ints = st.tuples(random_int, random_int, random_int)


@given(three_ints, three_ints, three_ints)
@settings(
    max_examples=10,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_apply_volume_limits(trade_sizes, min_trade_sizes, volume_limits):
    coins = ["SYM0", "SYM1", "SYM2"]
    pairs = [("SYM0", "SYM1"), ("SYM0", "SYM2"), ("SYM1", "SYM2")]

    arb_trades = [ArbTrade(*pair, size, 0) for pair, size in zip(pairs, trade_sizes)]
    limits = dict(zip(pairs, volume_limits))
    pool = DummyPool(dict(zip(coins, min_trade_sizes)))

    limited_arb_trades, excluded_trades = _apply_volume_limits(arb_trades, limits, pool)

    for trade in limited_arb_trades:
        assert trade.amount_in <= limits[trade.coin_in, trade.coin_out]
        assert trade.amount_in > pool.get_min_trade_size(trade.coin_in)

    for trade in excluded_trades:
        assert trade.amount_in <= pool.get_min_trade_size(trade.coin_in)
