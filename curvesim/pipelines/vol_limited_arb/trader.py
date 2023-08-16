from numpy import isnan
from scipy.optimize import least_squares

from curvesim.logging import get_logger
from curvesim.templates.trader import Trade, Trader

from ..common import get_arb_trades

logger = get_logger(__name__)


class VolumeLimitedArbitrageur(Trader):
    """
    Computes, executes, and reports out arbitrage trades.
    """

    def compute_trades(self, prices, volume_limits):  # pylint: disable=arguments-differ
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

        trades, errors, _ = multipair_optimal_arbitrage(
            self.pool, prices, volume_limits
        )
        return trades, {"price_errors": errors}


def multipair_optimal_arbitrage(  # noqa: C901  pylint: disable=too-many-locals
    pool, prices, limits
):
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

                coin_in, coin_out = pair
                min_size = pool.get_min_trade_size(coin_in)
                if dx > min_size:
                    pool.trade(coin_in, coin_out, dx)

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
            coin_in, coin_out = coins[k]
            min_size = pool.get_min_trade_size(coin_in)
            if amount_in > min_size:
                trades.append(Trade(coin_in, coin_out, amount_in))

        errors = res.fun

    except Exception:
        logger.error(
            "Optarbs args: x0: %s, lo: %s, hi: %s, prices: %s",
            sizes,
            lo,
            hi,
            price_targets,
            exc_info=True,
        )
        errors = post_trade_price_error_multi([0] * len(sizes), price_targets, coins)
        res = []

    return trades, errors, res
