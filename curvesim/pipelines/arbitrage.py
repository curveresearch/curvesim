"""
Implements the volume-limited arbitrage pipeline.
"""

import os
from functools import partial

from numpy import array, isnan
from scipy.optimize import least_squares, root_scalar

from curvesim.iterators.param_samplers import Grid
from curvesim.iterators.price_samplers import PriceVolume
from curvesim.logging import get_logger
from curvesim.metrics import StateLog, init_metrics, make_results
from curvesim.metrics import metrics as Metrics
from curvesim.pool import get_sim_pool
from curvesim.pool_data.cache import PoolDataCache

from .templates import TradeData, run_pipeline
from .utils import compute_volume_multipliers

logger = get_logger(__name__)


# pylint: disable-next=too-many-arguments
def volume_limited_arbitrage(
    pool_metadata,
    pool_data_cache=None,
    variable_params=None,
    fixed_params=None,
    metrics=None,
    test=False,
    days=60,
    src="coingecko",
    data_dir="data",
    vol_mult=None,
    vol_mode=1,
    ncpu=None,
    end=None,
):
    """
    Implements the volume-limited arbitrage pipeline.

    At each timestep, the pool is arbitraged as close to the prevailing market price
    as possible without surpassing a volume constraint. By default, volume is limited
    to the total market volume at each timestep, scaled by the proportion of
    volume attributable to the pool over the whole simulation period (vol_mult).

    Parameters
    ----------
    pool_metadata : :class:`~curvesim.pool_data.metadata.PoolMetaDataInterface`
        Pool metadata object for the pool of interest.

    variable_params : dict, defaults to broad range of A/fee values
        Pool parameters to vary across simulations.
        keys: pool parameters, values: iterables of ints

        Example
        --------
        >>> variable_params = {"A": [100, 1000], "fee": [10**6, 4*10**6]}

    fixed_params : dict, optional
        Pool parameters set before all simulations.
        keys: pool parameters, values: ints

        Example
        --------
        >>> fixed_params = {"D": 1000000*10**18}

    test : bool, optional
        Overrides variable_params to use four test values:

        .. code-block::

            {"A": [100, 1000], "fee": [3000000, 4000000]}

    days : int, default=60
        Number of days to pull pool and price data for.

    src : str, default="coingecko"
        Source for price/volume data: "coingecko" or "local".

    data_dir : str, default="data"
        relative path to saved price data folder

    vol_mult : float or numpy.ndarray, default computed from data
        Value(s) multiplied by market volume to specify volume limits
        (overrides vol_mode).

        Can be a scalar or vector with values for each pairwise coin combination.

    vol_mode : int, default=1
        Modes for limiting trade volume.

        1: limits trade volumes proportionally to market volume for each pair

        2: limits trade volumes equally across pairs

        3: mode 2 for trades with meta-pool asset, mode 1 for basepool-only trades

    ncpu : int, default=os.cpu_count()
        Number of cores to use.

    Returns
    -------
    dict

    """
    if test:
        variable_params = TEST_PARAMS

    if ncpu is None:
        cpu_count = os.cpu_count()
        ncpu = cpu_count if cpu_count is not None else 1

    variable_params = variable_params or DEFAULT_PARAMS
    metrics = metrics or DEFAULT_METRICS

    if pool_data_cache is None:
        pool_data_cache = PoolDataCache(pool_metadata, days=days, end=end)

    pool = get_sim_pool(pool_metadata, pool_data_cache=pool_data_cache)
    coins = pool_metadata.coins

    param_sampler = Grid(pool, variable_params, fixed_params=fixed_params)
    price_sampler = PriceVolume(coins, days=days, data_dir=data_dir, src=src, end=end)

    if vol_mult is None:
        total_pool_volume = pool_data_cache.volume
        total_market_volume = price_sampler.total_volumes()
        vol_mult = compute_volume_multipliers(
            total_pool_volume,
            total_market_volume,
            pool_metadata.n,
            pool_metadata.pool_type,
            mode=vol_mode,
        )

    metrics = init_metrics(metrics, pool=pool, freq=price_sampler.freq)
    strat = partial(strategy, metrics=metrics, vol_mult=vol_mult)

    output = run_pipeline(param_sampler, price_sampler, strat, ncpu=ncpu)
    results = make_results(*output, metrics)

    return results


# Strategy
def strategy(pool, parameters, price_sampler, metrics, vol_mult):
    """
    Computes and executes volume-limited arbitrage trades at each timestep.

    Parameters
    ----------
    pool : Pool, MetaPool, or RaiPool
        The pool to be arbitraged.

    parameters : dict
        Current pool parameters from the param_sampler (only used for logging/display).

    price_sampler : iterator
        Iterator that returns prices and volumes at each timestep.

    vol_mult : float or numpy.ndarray
        Value(s) multiplied by market volume to specify volume limits.

        Can be a scalar or vector with values for each pairwise coin combination.

    Returns
    -------
    metrics : tuple of lists

    """
    trader = Arbitrageur(pool)
    state_log = StateLog(pool, metrics)

    symbol = pool.symbol
    logger.info(f"[{symbol}] Simulating with {parameters}")

    for price_sample in price_sampler:
        volume_limits = price_sample.volumes * vol_mult
        pool.prepare_for_trades(price_sample.timestamp)
        trade_data = trader.arb_pool(price_sample.prices, volume_limits)
        state_log.update(price_sample=price_sample, trade_data=trade_data)

    return state_log.compute_metrics()


class Arbitrageur:
    """
    Computes, executes, and reports out arbitrage trades.
    """

    def __init__(self, pool):
        """
        Parameters
        ----------
        pool :
            Simulation interface to a subclass of :class:`.Pool`.

        """
        self.pool = pool

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

    def do_trades(self, trades):
        """
        Executes a series of trades.

        Parameters
        ----------
        trades : list of tuples
            Trades to execute, formatted as (coin_in, coin_out, trade_size).

        Returns
        -------
        trades_done: list of tuples
            Trades executed, formatted as (coin_in, coin_out, amount_in, amount_out).

        volume : int
            Total volume of trades in 18 decimal precision.

        """
        if len(trades) == 0:
            return [], 0

        total_volume = 0
        trades_done = []
        for trade in trades:
            i, j, dx = trade
            dy, fee, volume = self.pool.trade(i, j, dx)
            trades_done.append((i, j, dx, dy, fee))

            total_volume += volume

        return trades_done, total_volume

    def arb_pool(self, prices, volume_limits):
        trades, price_errors, _ = self.compute_trades(prices, volume_limits)
        trades_done, volume = self.do_trades(trades)
        return TradeData(trades_done, volume, volume_limits, price_errors)


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
    ) = pool.make_error_fns()
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


# Defaults
DEFAULT_METRICS = [
    Metrics.Timestamp,
    Metrics.PoolValue,
    Metrics.PoolBalance,
    Metrics.PriceDepth,
    Metrics.ArbMetrics,
]

DEFAULT_PARAMS = {
    "A": [int(2 ** (a / 2)) for a in range(12, 28)],
    "fee": list(range(1000000, 5000000, 1000000)),
}

TEST_PARAMS = {"A": [100, 1000], "fee": [3000000, 4000000]}
