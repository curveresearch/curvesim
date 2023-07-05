from numpy import isnan
from scipy.optimize import least_squares, root_scalar

from curvesim.logging import get_logger
from curvesim.templates.trader import Trade, Trader

logger = get_logger(__name__)


class VolumeLimitedArbitrageur(Trader):
    """
    Computes, executes, and reports out arbitrage trades.
    """

    def compute_trades(self, prices, volume_limits):
        """
        Computes trades to optimally arbitrage the pool, constrained by volume limits.

        Parameters
        ----------
        prices : dict
            Current market prices from the price_sampler.

        volume_limits : dict
            Current volume limits for each trading pair.


        Returns
        -------
        trades : list of :class:`Trade` objects
            List of trades to perform.

        additional_data: dict
            Dict of additional data to be passed to the state log as part of trade_data.
        """

        trades, errors, res = multipair_optimal_arbitrage(
            self.pool, prices, volume_limits
        )
        return trades, {"price_errors": errors}


def multipair_optimal_arbitrage(pool, prices, limits):  # noqa: C901
    """
    Computes trades to optimally arbitrage the pool, constrained by volume limits.

    Parameters
    ----------
    pool :
        Simulation interface to a subclass of :class:`Pool`.

    prices : dict
        Current market prices from the price_sampler.

    volume_limits : dict
        Current volume limits for each trading pair.

    Returns
    -------
    trades : List[Tuple]
        List of trades to perform.
        Trades are formatted as (coin_i, coin_j, trade_size)

    errors : List[Float]
        Post-trade price error between pool price and market price for each token pair.

    res : scipy.optimize.OptimizeResult
        Results object from the numerical optimizer.
    """
    init_trades = get_arb_trades(pool, prices)

    # Limit trade size, add size bounds
    limited_init_trades = []
    for t in init_trades:
        size, pair, price_target = t
        limit = int(limits[pair] * 10**18)
        t = min(size, limit), pair, price_target, 0, limit + 1
        limited_init_trades.append(t)

    # Order trades in terms of expected size
    limited_init_trades = sorted(limited_init_trades, reverse=True, key=lambda t: t[0])
    sizes, coins, price_targets, lo, hi = zip(*limited_init_trades)

    def post_trade_price_error_multi(dxs, price_targets, coins):
        with pool.use_snapshot_context():
            for k, pair in enumerate(coins):
                if isnan(dxs[k]):
                    dx = 0
                else:
                    dx = int(dxs[k])

                if dx > 0:
                    pool.trade(*pair, dx)

            errors = []
            for k, pair in enumerate(coins):
                price = pool.price(*pair, use_fee=True)
                errors.append(price - price_targets[k])

        return errors

    # Find trades that minimize difference between
    # pool price and external market price
    trades = []
    try:
        res = least_squares(
            post_trade_price_error_multi,
            x0=sizes,
            args=(price_targets, coins),
            bounds=(lo, hi),
            gtol=10**-15,
            xtol=10**-15,
        )

        # Format trades into tuples, ignore if dx=0
        dxs = res.x

        for k, amount_in in enumerate(dxs):
            if isnan(amount_in):
                continue

            amount_in = int(amount_in)
            if amount_in > 0:
                trades.append(Trade(*coins[k], amount_in))

        errors = res.fun

    except Exception:
        logger.error(
            f"Optarbs args: x0: {sizes}, lo: {lo}, hi: {hi}, prices: {price_targets}",
            exc_info=True,
        )
        errors = post_trade_price_error_multi([0] * len(sizes), price_targets, coins)
        res = []

    return trades, errors, res


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
            if dx > 0:
                pool.trade(coin_in, coin_out, int(dx))
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
