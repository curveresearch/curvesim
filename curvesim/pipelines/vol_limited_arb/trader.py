from itertools import combinations

from numpy import array, isnan
from scipy.optimize import least_squares, root_scalar

from curvesim.logging import get_logger
from curvesim.pipelines.templates.trader import Trader
from curvesim.pool.stableswap.metapool import CurveMetaPool
from curvesim.pool.stableswap.pool import CurvePool
from curvesim.pool.stableswap.raipool import CurveRaiPool

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

    all_idx = range(pool.n_total)
    index_combos = combinations(all_idx, 2)

    def get_trade_bounds(i, j):
        xp_j = int(xp[j] * 0.01)
        high = pool.get_y(j, i, xp_j, xp) - xp[i]
        return (0, high)

    def post_trade_price_error(dx, i, j, price_target):
        dx = int(dx) * 10**18 // pool.rates[i]

        with pool.use_snapshot_context():
            if dx > 0:
                pool.exchange(i, j, dx)

            dydx = pool.dydxfee(i, j)

        return dydx - price_target

    def post_trade_price_error_multi(dxs, price_targets, coins):
        with pool.use_snapshot_context():
            # Do trades
            for k, pair in enumerate(coins):
                i, j = pair

                if isnan(dxs[k]):
                    dx = 0
                else:
                    dx = int(dxs[k]) * 10**18 // pool.rates[i]

                if dx > 0:
                    pool.exchange(i, j, dx)

            # Record price errors
            errors = []
            for k, pair in enumerate(coins):
                i, j = pair
                dydx = pool.dydxfee(i, j)
                errors.append(dydx - price_targets[k])

        return errors

    return (
        get_trade_bounds,
        post_trade_price_error,
        post_trade_price_error_multi,
        index_combos,
    )


def make_error_fns_for_metapool(pool):  # noqa: C901
    # Note: for performance, does not support string coin-names

    max_coin = pool.max_coin

    p_all = [pool.rate_multiplier] + pool.basepool.rates
    xp_meta = pool._xp_mem(pool.balances, pool.rates)
    xp_base = pool._xp_mem(pool.basepool.balances, pool.basepool.rates)

    all_idx = range(pool.n_total)
    index_combos = combinations(all_idx, 2)

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

    def post_trade_price_error(dx, i, j, price_target):
        dx = int(dx) * 10**18 // p_all[i]

        with pool.use_snapshot_context():
            if dx > 0:
                pool.exchange_underlying(i, j, dx)

            dydx = pool.dydxfee(i, j)

        return dydx - price_target

    def post_trade_price_error_multi(dxs, price_targets, coins):
        with pool.use_snapshot_context():
            # Do trades
            for k, pair in enumerate(coins):
                i, j = pair

                if isnan(dxs[k]):
                    dx = 0
                else:
                    dx = int(dxs[k]) * 10**18 // p_all[i]

                if dx > 0:
                    pool.exchange_underlying(i, j, dx)

            # Record price errors
            errors = []
            for k, pair in enumerate(coins):
                i, j = pair
                dydx = pool.dydxfee(i, j)
                errors.append(dydx - price_targets[k])

        return errors

    return (
        get_trade_bounds,
        post_trade_price_error,
        post_trade_price_error_multi,
        index_combos,
    )


pool_type_to_error_functions = {
    CurvePool: make_error_fns,
    CurveMetaPool: make_error_fns_for_metapool,
    CurveRaiPool: make_error_fns_for_metapool,
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
    (
        get_bounds,
        error_function,
        error_function_multi,
        index_combos,
    ) = pool_type_to_error_functions[type(pool)](pool)
    x0, lo, hi, coins, price_targets = get_trade_args(
        pool.price,
        get_bounds,
        error_function,
        prices,
        limits,
        index_combos,
    )

    # Order trades in terms of expected size
    order = sorted(range(len(x0)), reverse=True, key=x0.__getitem__)
    x0 = [x0[i] for i in order]
    lo = [lo[i] for i in order]
    hi = [hi[i] for i in order]
    coins = [coins[i] for i in order]
    price_targets = [price_targets[i] for i in order]

    # Find trades that minimize difference between
    # pool price and external market price
    trades = []
    try:
        res = least_squares(
            error_function_multi,
            x0=x0,
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
            f"Optarbs args: x0: {x0}, lo: {lo}, hi: {hi}, prices: {price_targets}",
            exc_info=True,
        )
        errors = array(error_function_multi([0] * len(x0), price_targets, coins))
        res = []

    return trades, errors, res


def get_trade_args(get_pool_price, get_bounds, error_function, prices, limits, combos):
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

    lo : list
        Lower bounds on trade sizes for each token pair

    hi: list
        Upper bounds on trade sizes for each token pair

    coins : list of tuples
        Ordered list of token pairs

    price_targets : list of floats
        Ordered list of price targets for each token pair

    """
    x0 = []
    lo = []
    hi = []
    coins = []
    price_targets = []

    for k, pair in enumerate(combos):
        i, j = pair
        limit = int(limits[k] * 10**18)
        lo.append(0)
        hi.append(limit + 1)

        if get_pool_price(i, j) - prices[k] > 0:
            price = prices[k]
            in_index = i
            out_index = j
        elif get_pool_price(j, i) - 1 / prices[k] > 0:
            price = 1 / prices[k]
            in_index = j
            out_index = i
        else:
            x0.append(0)
            coins.append((i, j))
            price_targets.append(prices[k])
            continue

        try:
            trade, _, _ = opt_arb(
                get_bounds, error_function, in_index, out_index, price
            )
            size = min(trade[2], limit)
            x0.append(size)
        except ValueError:
            pool_price = get_pool_price(in_index, out_index)
            logger.error(
                f"Opt_arb error: Pair: {(in_index, out_index)}, Pool price: {pool_price},"
                f"Target Price: {price}, Diff: {pool_price - price}"
            )
            x0.append(0)

        coins.append((in_index, out_index))
        price_targets.append(price)

    return x0, lo, hi, coins, price_targets
