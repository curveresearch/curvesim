from itertools import combinations

from numpy import array
from scipy.optimize import root_scalar

from curvesim.logging import get_logger
from curvesim.pipelines.templates.trader import Trader

logger = get_logger(__name__)


class SimpleArbitrageur(Trader):
    """
    Computes, executes, and reports out arbitrage trades.
    """

    def compute_trades(self, prices):
        """
        Compute trades to arbitrage the pool, as follows:
            1. For each coin pair i and j, calculate size of coin i
               needed to move price of coin i w.r.t. to j to the
               target price.
            2. Calculate the profit from each such swap.
            3. Take the swap that gives the largest profit.

        Parameters
        ----------
        prices : pandas.Series
            Current market prices from the price_sampler.

        Returns
        -------
        trades: List[Tuple]
            List of trades to perform.

            Each trade is a tuple (coin_in, coin_out, size).

            "coin_in": in token
            "coin_out": out token
            "size": trade size

        price_errors: List[float]
            Differences between resulting pool price and target price

        optimizer_result: object
            Optional object holding any useful debugging information
            for the arbitraging algorithms
        """
        pool = self.pool
        trades = get_arb_trades(pool, prices)

        max_profit = 0
        best_trade = None
        price_error = None
        for t in trades:
            size, coins, price_target = t
            i, j = coins
            with pool.use_snapshot_context():
                out_amount, _, _ = pool.trade(i, j, size)
                profit = out_amount - size * price_target
                if profit > max_profit:
                    max_profit = profit
                    best_trade = i, j, size
                    price_error = pool.price(i, j) - price_target

        if not best_trade:
            return [], array([]), None

        return [best_trade], array([price_error]), None


def get_arb_trades(pool, prices):
    """
    Returns triples of "trades", one for each coin pair in `combo`.

    Each trade is a triple consisting of size, ordered coin-pair,
    and price target to move the pool price to.

    Parameters
    ----------
    pool: SimPool
        Pool to arbitrage on

    error_function: callable
        Error function that returns the difference between pool price and
        market price (p) after some trade (coin_i, coin_j, trade_size)

    prices : iterable
        External market prices for each coin-pair

    combos : iterable of tuples
        Ordered pairwise combinations of coin indices

    Returns
    -------
    trades: List[Tuple]
        List of triples (size, coins, price_target)
        "size": trade size
        "coins": in token, out token
        "price_target": price target for arbing the token pair
    """
    all_idx = range(pool.number_of_coins)
    index_combos = list(combinations(all_idx, 2))

    def post_trade_price_error(dx, i, j, price_target):
        with pool.use_snapshot_context():
            if dx > 0:
                pool.trade(i, j, dx)
            price = pool.price(i, j, use_fee=True)

        return price - price_target

    trades = []

    for k, pair in enumerate(index_combos):
        i, j = pair

        if pool.price(i, j) > prices[k]:
            price = prices[k]
            in_index = i
            out_index = j
        elif pool.price(j, i) > 1 / prices[k]:
            price = 1 / prices[k]
            in_index = j
            out_index = i
        else:
            trades.append((0, (i, j), prices[k]))
            continue

        high = pool.get_in_amount(in_index, out_index, out_balance_perc=0.01)
        bounds = (0, high)
        try:
            res = root_scalar(
                post_trade_price_error,
                args=(in_index, out_index, price),
                bracket=bounds,
                method="brentq",
            )
            size = int(res.root)
        except ValueError:
            pool_price = pool.price(in_index, out_index)
            logger.error(
                f"Opt_arb error: Pair: {(in_index, out_index)}, Pool price: {pool_price},"
                f"Target Price: {price}, Diff: {pool_price - price}"
            )
            size = 0

        trades.append((size, (in_index, out_index), price))

    return trades
