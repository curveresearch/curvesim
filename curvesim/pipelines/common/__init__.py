"""
Contains variables and functions common to the arbitrage pipelines.
"""
__all__ = ["DEFAULT_METRICS", "get_arb_trades", "get_asset_data", "get_pool_data"]

from scipy.optimize import root_scalar

from curvesim.logging import get_logger
from curvesim.metrics import metrics as Metrics
from curvesim.templates.trader import ArbTrade

from .get_asset_data import get_asset_data
from .get_pool_data import get_pool_data

logger = get_logger(__name__)
DEFAULT_METRICS = [
    Metrics.Timestamp,
    Metrics.PoolValue,
    Metrics.PoolBalance,
    Metrics.PriceDepth,
    Metrics.PoolVolume,
    Metrics.ArbMetrics,
]


def get_arb_trades(pool, prices):
    """
    Returns triples of "trades", one for each coin pair in `combo`.

    Each trade is a triple consisting of size, ordered coin-pair,
    and price target to move the pool price to.

    Parameters
    ----------
    pool: SimPool
        Pool to arbitrage on

    prices : iterable
        External market prices for each coin-pair


    Returns
    -------
    trades: List[Tuple]
        List of triples (size, coins, price_target)
        "size": trade size
        "coins": in token, out token
        "price_target": price target for arbing the token pair
    """

    def post_trade_price_error(dx, coin_in, coin_out, price_target):
        with pool.use_snapshot_context():
            dx = int(dx)
            if dx > 0:
                pool.trade(coin_in, coin_out, dx)
            price = pool.price(coin_in, coin_out, use_fee=True)

        return price - price_target

    trades = []

    for pair in prices:
        coin_in, coin_out, target_price = _get_arb_direction(pair, pool, prices[pair])

        lower_bound = pool.get_min_trade_size(coin_in)
        profit_per_unit = post_trade_price_error(
            lower_bound, coin_in, coin_out, target_price
        )
        if profit_per_unit <= 0:
            trades.append(ArbTrade(coin_in, coin_out, 0, target_price))
            continue

        upper_bound = pool.get_max_trade_size(coin_in, coin_out)
        try:
            res = root_scalar(
                post_trade_price_error,
                args=(coin_in, coin_out, target_price),
                bracket=(lower_bound, upper_bound),
                method="brentq",
            )
            size = int(res.root)
        except ValueError:
            pool_price = pool.price(coin_in, coin_out)
            logger.error(
                "Opt_arb error: Pair: (%s, %s), Pool price: %s,"
                "Target Price: %s, Diff: %s",
                coin_in,
                coin_out,
                pool_price,
                target_price,
                pool_price - target_price,
            )
            size = 0

        trades.append(ArbTrade(coin_in, coin_out, size, target_price))

    return trades


def _get_arb_direction(pair, pool, market_price):
    i, j = pair
    price_error_i = pool.price(i, j) - market_price
    price_error_j = pool.price(j, i) - 1 / market_price

    if price_error_i >= price_error_j:
        target_price = market_price
        coin_in, coin_out = i, j
    else:
        target_price = 1 / market_price
        coin_in, coin_out = j, i

    return coin_in, coin_out, target_price
