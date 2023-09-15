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
    arb_trades = get_arb_trades(pool, prices)
    limited_arb_trades = apply_volume_limits(arb_trades, limits, pool)
    limited_arb_trades = sort_trades_by_size(limited_arb_trades)
    least_squares_inputs = make_least_squares_inputs(limited_arb_trades, limits)

    def post_trade_price_error_multi(amounts_in, price_targets, coin_pairs):
        with pool.use_snapshot_context():
            for coin_pair, amount_in in zip(coin_pairs, amounts_in):
                if isnan(amount_in):
                    dx = 0
                else:
                    dx = int(amount_in)

                min_size = pool.get_min_trade_size(coin_pair[0])
                if dx > min_size:
                    pool.trade(*coin_pair, dx)

            errors = []
            for coin_pair, price_target in zip(coin_pairs, price_targets):
                price = pool.price(*coin_pair, use_fee=True)
                errors.append(price - price_target)

        return errors

    # Find trades that minimize difference between
    # pool price and external market price
    trades = []
    try:
        res = least_squares(
            post_trade_price_error_multi,
            **least_squares_inputs,
            gtol=10**-15,
            xtol=10**-15,
        )

        # Record optimized trades
        optimized_amounts_in = res.x

        for amount_in, trade in zip(optimized_amounts_in, limited_arb_trades):
            if isnan(amount_in):
                continue

            amount_in = int(amount_in)
            min_size = pool.get_min_trade_size(trade.coin_in)
            if amount_in > min_size:
                trades.append(Trade(trade.coin_in, trade.coin_out, amount_in))

        errors = res.fun

    except Exception:
        logger.error(
            "Optarbs args: x0: %s, bounds: %s, prices: %s",
            least_squares_inputs["x0"],
            least_squares_inputs["bounds"],
            least_squares_inputs["kwargs"]["price_targets"],
            exc_info=True,
        )
        errors = post_trade_price_error_multi(
            [0] * len(limited_arb_trades), **least_squares_inputs["kwargs"]
        )
        res = []

    return trades, errors, res


def apply_volume_limits(arb_trades, limits, pool):
    """
    Returns list of ArbTrades with amount_in set to min(limit, amount_in). Any trades
    limited to less than the pool's minimum trade size are excluded.
    """

    limited_arb_trades = []
    for trade in arb_trades:
        pair = trade.coin_in, trade.coin_out
        limited_amount_in = min(limits[pair], trade.amount_in)
        lim_trade = trade.replace_amount_in(limited_amount_in)

        # if lim_trade.amount_in > pool.get_min_trade_size(lim_trade.coin_in):
        limited_arb_trades.append(lim_trade)

    return limited_arb_trades


def sort_trades_by_size(trades):
    """Sorts trades by amount_in."""
    sorted_trades = sorted(trades, reverse=True, key=lambda t: t.amount_in)
    return sorted_trades


def make_least_squares_inputs(trades, limits):
    """
    Returns a dict of trades, bounds, and targets formatted as kwargs for least_squares.
    """

    coins_in, coins_out, amounts_in, price_targets = zip(*trades)
    coin_pairs = zip(coins_in, coins_out)

    low_bound = [0] * len(trades)
    high_bound = [limits[pair] + 1 for pair in coin_pairs]

    return {
        "x0": amounts_in,
        "kwargs": {"price_targets": price_targets, "coin_pairs": coin_pairs},
        "bounds": (low_bound, high_bound),
    }
