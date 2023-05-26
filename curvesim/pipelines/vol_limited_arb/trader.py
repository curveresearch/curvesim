from itertools import combinations

from numpy import array, isnan
from scipy.optimize import least_squares, root_scalar

from curvesim.logging import get_logger
from curvesim.pipelines.templates.trader import Trader
from curvesim.pool.sim_interface import SimCurveMetaPool, SimCurvePool, SimCurveRaiPool

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
        prices : pandas.Series
            Current market prices from the price_sampler.

        volume_limits : pandas.Series
            Current volume limits.

        Returns
        -------
        trades : list of tuples
            List of trades to perform.
            Trades are formatted as (coin_in, coin_out, trade_size).

        errors : numpy.ndarray
            Post-trade price error between pool price and market price.

        res : scipy.optimize.OptimizeResult
            Results object from the numerical optimizer.

        """
        trades, errors, res = opt_arb_multi(self.pool, prices, volume_limits)
        return trades, errors, res


# Optimizers
def opt_arb(get_bounds, error_function, i, j, p):
    """
    Estimates a single trade to optimally arbitrage coin[i] for coin[j] given
    external price p (base: i, quote: j).

    p must be less than dy[j]/dx[i], including fees.

    Parameters
    ----------
    get_bounds : callable
        Function that returns bounds on trade size hypotheses for any
        token pairs (i,j).

    error_function: callable
        Error function that returns the difference between pool price and
        market price (p) after some trade (coin_i, coin_j, trade_size)

    i : int
        Index for the input coin (base)

    j : int
        Index for the output coin (quote)

    p : float
        External market price to arbitrage the pool to

    Returns
    -------
    trade : tuple
        Trades to perform, formatted as (coin_i, coin_j, trade_size).

    error : numpy.ndarray
        Post-trade price error between pool price and market price.

    res : scipy.optimize.OptimizeResult
        Results object from the numerical optimizer.

    """
    bounds = get_bounds(i, j)
    res = root_scalar(error_function, args=(i, j, p), bracket=bounds, method="brentq")

    trade = (i, j, int(res.root))
    error = error_function(int(res.root), i, j, p)

    return trade, error, res


def make_error_fns(pool):  # noqa: C901
    """
    Returns the pricing error functions needed for determining the
    optimal arbitrage in simulations.

    Note
    ----
    For performance, does not support string coin-names.
    """
    xp = pool._xp_mem(pool.balances, pool.rates)

    def get_trade_bounds(i, j):
        xp_j = int(xp[j] * 0.01)
        high = pool.get_y(j, i, xp_j, xp) - xp[i]
        return (0, high)

    return get_trade_bounds


def make_error_fns_for_metapool(pool):  # noqa: C901
    # Note: for performance, does not support string coin-names

    max_coin = pool.max_coin

    xp_meta = pool._xp_mem(pool.balances, pool.rates)
    xp_base = pool._xp_mem(pool.basepool.balances, pool.basepool.rates)

    def get_trade_bounds(i, j):
        base_i = i - max_coin
        base_j = j - max_coin
        meta_i = max_coin
        meta_j = max_coin
        if base_i < 0:
            meta_i = i
        if base_j < 0:
            meta_j = j

        if base_i < 0 or base_j < 0:
            xp_j = int(xp_meta[meta_j] * 0.01)
            high = pool.get_y(meta_j, meta_i, xp_j, xp_meta)
            high -= xp_meta[meta_i]
        else:
            xp_j = int(xp_base[base_j] * 0.01)
            high = pool.basepool.get_y(base_j, base_i, xp_j, xp_base)
            high -= xp_base[base_i]

        return (0, high)

    return get_trade_bounds


pool_type_to_error_functions = {
    SimCurvePool: make_error_fns,
    SimCurveMetaPool: make_error_fns_for_metapool,
    SimCurveRaiPool: make_error_fns_for_metapool,
}


def opt_arb_multi(pool, prices, limits):  # noqa: C901
    """
    Computes trades to optimally arbitrage the pool, constrained by volume limits.

    Parameters
    ----------
    pool :
        Simulation interface to a subclass of :class:`Pool`.

    prices : pandas.Series
        Current market prices from the price_sampler

    volume_limits : pandas.Series
        Current volume limits

    Returns
    -------
    trades : list of tuples
        List of trades to perform.
        Trades are formatted as (coin_i, coin_j, trade_size)

    errors : numpy.ndarray
        Post-trade price error between pool price and market price for each token pair.

    res : scipy.optimize.OptimizeResult
        Results object from the numerical optimizer.

    """
    all_idx = range(pool.n_total)
    index_combos = combinations(all_idx, 2)

    get_bounds = pool_type_to_error_functions[type(pool)](pool)
    initial_trades = get_arb_trades(
        pool,
        get_bounds,
        prices,
        index_combos,
    )

    lo = []
    hi = []
    for k, pair in enumerate(index_combos):
        i, j = pair
        limit = int(limits[k] * 10**18)
        lo.append(0)
        hi.append(limit + 1)
        # limit trade size
        size, coin, price_target = initial_trades[k]
        initial_trades[k] = min(size, limit), coin, price_target

    # Order trades in terms of expected size
    initial_trades = sorted(initial_trades, reverse=True, key=lambda t: t[0])
    sizes, coins, price_targets = zip(*initial_trades)

    def post_trade_price_error_multi(dxs, price_targets, coins):
        with pool.use_snapshot_context():
            for k, pair in enumerate(coins):
                i, j = pair

                if isnan(dxs[k]):
                    dx = 0
                else:
                    dx = int(dxs[k])

                if dx > 0:
                    pool.trade(i, j, dx)

            errors = []
            for k, pair in enumerate(coins):
                i, j = pair
                price = pool.price(i, j, use_fee=True)
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

        for k, dx in enumerate(dxs):
            if isnan(dx):
                continue

            dx = int(dx)
            if dx > 0:
                i = coins[k][0]
                j = coins[k][1]
                trades.append((i, j, dx))

        errors = res.fun

    except Exception:
        logger.error(
            f"Optarbs args: x0: {sizes}, lo: {lo}, hi: {hi}, prices: {price_targets}",
            exc_info=True,
        )
        errors = array(
            post_trade_price_error_multi([0] * len(sizes), price_targets, coins)
        )
        res = []

    return trades, errors, res


def get_arb_trades(pool, get_bounds, prices, combos):
    """
    Returns initial guesses (x0), bounds (lo, hi), ordered coin-pairs, and
    price targets used to estimate the optimal set of arbitrage trades.

    Parameters
    ----------
    get_pool_price : callable
        Function that returns the pool price for any token pair (i,j)

    get_bounds : callable
        Function that returns bounds on trade size hypotheses for
        any token pairs (i,j).

    error_function: callable
        Error function that returns the difference between pool price and
        market price (p) after some trade (coin_i, coin_j, trade_size)

    prices : iterable
        External market prices for each coin-pair

    combos : iterable of tuples
        Ordered pairwise combinations of coin indices

    Returns
    -------
    x0 : list
        Initial "guess" values for trade size for each token pair

    coins : list of tuples
        Ordered list of token pairs

    price_targets : list of floats
        Ordered list of price targets for each token pair

    """

    def post_trade_price_error(dx, i, j, price_target):
        with pool.use_snapshot_context():
            if dx > 0:
                pool.trade(i, j, dx)

            price = pool.price(i, j, use_fee=True)

        return price - price_target

    trades = []

    for k, pair in enumerate(combos):
        i, j = pair

        if pool.price(i, j) - prices[k] > 0:
            price = prices[k]
            in_index = i
            out_index = j
        elif pool.price(j, i) - 1 / prices[k] > 0:
            price = 1 / prices[k]
            in_index = j
            out_index = i
        else:
            trades.append((0, (i, j), prices[k]))
            continue

        try:
            trade, _, _ = opt_arb(
                get_bounds, post_trade_price_error, in_index, out_index, price
            )
            size = trade[2]
        except ValueError:
            pool_price = pool.price(in_index, out_index)
            logger.error(
                f"Opt_arb error: Pair: {(in_index, out_index)}, Pool price: {pool_price},"
                f"Target Price: {price}, Diff: {pool_price - price}"
            )
            size = 0

        trades.append(size, (in_index, out_index), price)

    return trades
