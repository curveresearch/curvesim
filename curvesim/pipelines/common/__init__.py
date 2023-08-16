from scipy.optimize import root_scalar

from curvesim.logging import get_logger
from curvesim.metrics import metrics as Metrics

logger = get_logger(__name__)
DEFAULT_METRICS = [
    Metrics.Timestamp,
    Metrics.PoolValue,
    Metrics.PoolBalance,
    # Metrics.PriceDepth,
    Metrics.PoolVolume,
    Metrics.ArbMetrics,
]

DEFAULT_PARAMS = {
    "A": [int(2 ** (a / 2)) for a in range(12, 28)],
    "fee": list(range(1000000, 5000000, 1000000)),
}

TEST_PARAMS = {"A": [100, 1000], "fee": [3000000, 4000000]}
TEST_CRYPTO_PARAMS = {
    "A": [270000, 2700000],
    "gamma": [1300000000000, 13000000000],
    "fee_gamma": [500000000000000, 50000000000000],
    "out_fee": [80000000, 800000000],
}


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
        i, j = pair

        if pool.price(i, j) - prices[pair] > 0:
            price = prices[pair]
            coin_in, coin_out = i, j
        elif pool.price(j, i) - 1 / prices[pair] > 0:
            price = 1 / prices[pair]
            coin_in, coin_out = j, i
        else:
            trades.append((0, pair, prices[pair]))
            continue

        high = pool.get_max_trade_size(coin_in, coin_out)
        bounds = (0, high)
        try:
            res = root_scalar(
                post_trade_price_error,
                args=(coin_in, coin_out, price),
                bracket=bounds,
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
                price,
                pool_price - price,
            )
            size = 0

        trades.append((size, (coin_in, coin_out), price))

    return trades
