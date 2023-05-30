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
    get_bounds = pool_type_to_error_functions[type(pool)](pool)
    init_trades = get_arb_trades(
        pool,
        get_bounds,
        prices,
    )

    # Limit trade size, add size bounds
    limited_init_trades = []
    for t, limit in zip(init_trades, limits):
        size, pair, price_target = t
        i, j = pair
        limit = int(limit * 10**18)
        t = min(size, limit), pair, price_target, 0, limit + 1
        limited_init_trades.append(t)

    # Order trades in terms of expected size
    limited_init_trades = sorted(limited_init_trades, reverse=True, key=lambda t: t[0])
    sizes, coins, price_targets, lo, hi = zip(*limited_init_trades)

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


def get_arb_trades(pool, get_bounds, prices):
    """
    Returns triples of "trades", one for each coin pair in `combo`.

    Each trade is a triple consisting of size, ordered coin-pair,
    and price target to move the pool price to.

    Parameters
    ----------
    pool: SimPool
        Pool to arbitrage on

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
    trades: List[Tuple]
        List of triples (size, coins, price_target)
        "size": trade size
        "coins": in token, out token
        "price_target": price target for arbing the token pair
    """
    # FIXME: `n_total` is not a SimPool property!
    all_idx = range(pool.n_total)
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

        bounds = get_bounds(in_index, out_index)
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
