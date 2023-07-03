from scipy.optimize import root_scalar

from curvesim.logging import get_logger
from curvesim.templates.trader import Trade, Trader

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
        trades : list of :class:`Trade` objects
            List of trades to perform.

        additional_data: dict
            Dict of additional data to be passed to the state log as part of trade_data.
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
                out_amount, _ = pool.trade(i, j, size)
                # assume we transacted at "infinite" depth at target price
                # on the other exchange to obtain our in-token
                profit = out_amount - size * price_target
                if profit > max_profit:
                    max_profit = profit
                    best_trade = Trade(i, j, size)
                    price_error = pool.price(i, j) - price_target

        if not best_trade:
            return [], {"price_errors": []}

        return [best_trade], {"price_errors": [price_error]}


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

    def post_trade_price_error(dx, coin_in, coin_out, price_target):
        with pool.use_snapshot_context():
            if dx > 0:
                pool.trade(coin_in, coin_out, int(dx))
            price = pool.price(coin_in, coin_out, use_fee=True)

        return price - price_target

    trades = []

    for pair in prices.keys():
        i, j = pair

        if pool.price(i, j) - prices[pair] > 0:
            price = prices[pair]
            coin_in = i
            coin_out = j
        elif pool.price(j, i) - 1 / prices[pair] > 0:
            price = 1 / prices[pair]
            coin_in = j
            coin_out = i
        else:
            trades.append((0, pair, prices[pair]))
            continue

        high = pool.get_in_amount(coin_in, coin_out, out_balance_perc=0.01)
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
                f"Opt_arb error: Pair: {(coin_in, coin_out)}, Pool price: {pool_price},"
                f"Target Price: {price}, Diff: {pool_price - price}"
            )
            size = 0

        trades.append((size, (coin_in, coin_out), price))

    return trades
