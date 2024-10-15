from pprint import pformat

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
    all_trades = get_arb_trades(pool, prices)
    input_trades, skipped_trades = _apply_volume_limits(all_trades, limits, pool)

    if not input_trades:
        price_errors = _make_price_errors(skipped_trades=skipped_trades, pool=pool)
        return [], price_errors, None

    input_trades = _sort_trades_by_size(input_trades)
    least_squares_inputs = _make_least_squares_inputs(input_trades, limits)

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
        for trade, amount_in in zip(input_trades, res.x):
            if isnan(amount_in):
                continue

            amount_in = int(amount_in)
            min_size = pool.get_min_trade_size(trade.coin_in)
            if amount_in > min_size:
                trades.append(Trade(trade.coin_in, trade.coin_out, amount_in))

        price_errors = _make_price_errors(input_trades, res.fun, skipped_trades, pool)

    except Exception:
        logger.error("Opt Arbs:\n %s", pformat(least_squares_inputs), exc_info=True)
        price_errors = _make_price_errors(skipped_trades=all_trades, pool=pool)
        res = None

    return trades, price_errors, res


def _apply_volume_limits(arb_trades, limits, pool):
    """
    Returns list of ArbTrades with amount_in set to min(limit, amount_in). Any trades
    limited to less than the pool's minimum trade size are excluded.
    """

    limited_arb_trades = []
    excluded_trades = []
    for trade in arb_trades:
        pair = trade.coin_in, trade.coin_out
        limited_amount_in = min(limits[pair], trade.amount_in)
        lim_trade = trade.replace_amount_in(limited_amount_in)

        if lim_trade.amount_in > pool.get_min_trade_size(lim_trade.coin_in):
            limited_arb_trades.append(lim_trade)
        else:
            excluded_trades.append(lim_trade)

    return limited_arb_trades, excluded_trades


def _sort_trades_by_size(trades):
    """Sorts trades by amount_in."""
    sorted_trades = sorted(trades, reverse=True, key=lambda t: t.amount_in)
    return sorted_trades


def _make_least_squares_inputs(trades, limits):
    """
    Returns a dict of trades, bounds, and targets formatted as kwargs for least_squares.
    """

    coins_in, coins_out, amounts_in, price_targets = zip(*trades)
    coin_pairs = tuple(zip(coins_in, coins_out))

    low_bound = [0] * len(trades)
    high_bound = [limits[pair] + 1 for pair in coin_pairs]

    return {
        "x0": amounts_in,
        "kwargs": {"price_targets": price_targets, "coin_pairs": coin_pairs},
        "bounds": (low_bound, high_bound),
    }


def _make_price_errors(trades=None, trade_errors=None, skipped_trades=None, pool=None):
    """
    Returns a dict mapping coin pairs to price errors.

    Parameters
    ----------
    trades :
        Trades input into the least_squares optimizer

    trade_errors :
        Price errors returned by the optimizer

    skipped_trades :
        Trades excluded from optimization

    pool :
        The pool used to compute the pool price for skipped trades

    Returns
    -------
    price_errors: Dict
        Maps coin pairs (tuple) to price_errors
    """
    price_errors = {}
    if trades:
        for trade, price_error in zip(trades, trade_errors):
            coin_pair = trade.coin_in, trade.coin_out
            price_errors[coin_pair] = price_error / trade.price_target

    if skipped_trades:
        for trade in skipped_trades:
            coin_pair = trade.coin_in, trade.coin_out
            price_error = pool.price(*coin_pair, use_fee=True) - trade.price_target
            price_errors[coin_pair] = price_error / trade.price_target

    return price_errors
