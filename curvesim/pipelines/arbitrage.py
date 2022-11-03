"""
Implements the volume-limited arbitrage pipeline.
"""

import traceback
from datetime import timedelta
from functools import partial

from numpy import array, exp, isnan, log
from pandas import DataFrame, MultiIndex
from scipy.optimize import least_squares, root_scalar

from ..iterators.param_samplers import Grid
from ..iterators.price_samplers import PriceVolume
from ..plot import saveplots
from ..pool.stableswap import StableSwapSimInterface
from ..pool.stableswap.functions import get_D, get_xp
from .templates import run_pipeline
from .utils import compute_volume_multipliers

DEFAULT_PARAMS = {
    "A": [int(2 ** (a / 2)) for a in range(12, 28)],
    "fee": list(range(1000000, 5000000, 1000000)),
}

TEST_PARAMS = {"A": [100, 1000], "fee": [3000000, 4000000]}


def volume_limited_arbitrage(
    pool_data,
    variable_params=DEFAULT_PARAMS,
    fixed_params=None,
    test=False,
    days=60,
    src="coingecko",
    data_dir="data",
    vol_mult=None,
    vol_mode=1,
    ncpu=4,
):
    """
    Implements the volume-limited arbitrage pipeline.

    At each timestep, the pool is arbitraged as close to the prevailing market price
    as possible without surpassing a volume constraint. By default, volume is limited
    to the total market volume at each timestep, multiplied by the ratio of historical
    pool volume to total market volume over the whole simulation period (vol_mult).

    Parameters
    ----------
    pool_data : pool_data.PoolData
        pool data object for the pool of interest

    variable_params : dict, defaults to broad range of A/fee values
        pool parameters to vary across simulations; keys: pool parameters,
        values: iterables of ints

        Example
        --------
        >>> variable_params = {"A": [100, 1000], "fee": [10**6, 4*10**6]}

    fixed_params : dict, optional
        pool parameters set before all simulations; keys: pool parameters,
        values: ints

        Example
        --------
        >>> fixed_params = {"D": 1000000*10**18}

    test : bool, optional
        Overrides variable_params to use only four test values

    days : int, default=60
        number of days to pull pool and price data for

    src : str, default="coingecko"
        source for price/volume data: coingecko, nomics, or local

    data_dir : str, default="data"
        relative path to saved price data folder

    vol_mult : float or numpy.ndarray, default computed from data
        value(s) multiplied by market volume to specify volume limits;
        can be a scalar or vector with entries for each pairwise coin combination

    vol_mode : int, default=1
        modes for limiting trade volume

        1: limits trade volumes proportionally to market volume for each pair

        2: limits trade volumes equally across pairs

        3: mode 2 for trades with meta-pool asset, mode 1 for basepool-only trades

    ncpu : int, default=4
        number of cores to use

    """

    if test:
        variable_params = TEST_PARAMS

    pool = pool_data.pool()
    coins = pool_data.coins()

    param_sampler = Grid(pool, variable_params, fixed_params=fixed_params)
    price_sampler = PriceVolume(coins, days=days, data_dir=data_dir, src=src)

    vol_args = (
        pool_data.volume(days=days),
        price_sampler.total_volumes(),
        pool_data.n(),
        pool_data.type(),
    )

    vol_mult = vol_mult or compute_volume_multipliers(*vol_args, mode=vol_mode)
    strat = partial(strategy, vol_mult=vol_mult)

    results = run_pipeline(param_sampler, price_sampler, strat, ncpu=ncpu)
    results = format_results(
        results, param_sampler.flat_grid(), price_sampler.prices.index
    )

    p_keys = sorted(variable_params.keys())
    if p_keys == ["A", "fee"]:
        saveplots(
            pool.metadata["symbol"].lower() + "_" + pool.metadata["address"][0:7],
            variable_params["A"],
            variable_params["fee"],
            results,
        )

    return results


# Strategy
def strategy(pool, params, price_sampler, vol_mult):
    pool_interface = StableSwapSimInterface(pool)
    trader = Arbitrageur(pool_interface)
    metrics = Metrics()

    symbol = pool_interface.pool.metadata["symbol"]
    print(f"[{symbol}] Simulating with {params}")

    for prices, volumes, timestamp in price_sampler:
        limits = volumes * vol_mult
        pool_interface.next_timestamp(timestamp)
        trades, errors, res = trader.compute_trades(prices, limits)
        trades_done, volume = trader.do_trades(trades)

        metrics.update(trader.pool_interface, errors, volume)

    return metrics()


class Arbitrageur:
    def __init__(self, pool_interface):
        self.pool_interface = pool_interface
        self.pool_precisions = pool_interface.precisions()
        self.max_coin = pool_interface.max_coin

    def compute_trades(self, prices, volume_limits):
        trades, errors, res = opt_arb_multi(self.pool_interface, prices, volume_limits)
        return trades, errors, res

    def do_trades(self, trades):
        if len(trades) == 0:
            return [], 0

        p = self.pool_precisions
        max_coin = self.max_coin

        volume = 0
        trades_done = []
        for trade in trades:
            i, j, dx = trade
            dy, dy_fee = self.pool_interface.trade(i, j, dx)
            trades_done.append(trade + (dy,))

            if max_coin:
                if i < max_coin or j < max_coin:
                    volume += dx * p[i] // 10**18  # in D units
            else:
                volume += dx * p[i] // 10**18  # in D units

        return trades_done, volume


# Metrics
class Metrics:
    def __init__(self):
        self.xs = []
        self.ps = []
        self.pool_balance = []
        self.pool_value = []
        self.price_depth = []
        self.price_error = []
        self.volume = []

    def __call__(self):
        records = (
            self.xs,
            self.ps,
            self.pool_balance,
            self.pool_value,
            self.price_depth,
            self.price_error,
            self.volume,
        )

        return records

    def update(self, pool_interface, errors, trade_volume):
        pool_state = pool_interface.get_pool_state()
        p = getattr(pool_state, "rates", pool_state.p)

        xp = get_xp(pool_state.x, p)
        bal = self.compute_balance(xp)
        price_depth = self.compute_price_depth(pool_interface)
        value = get_D(xp, pool_state.A) / 10**18

        self.xs.append(pool_state.x)
        self.ps.append(p)
        self.pool_balance.append(bal)
        self.pool_value.append(value)
        self.price_depth.append(sum(price_depth) / len(price_depth))
        self.price_error.append(sum(abs(errors)))
        self.volume.append(trade_volume / 10**18)

    @staticmethod
    def compute_balance(xp):
        n = len(xp)
        xp = array(xp)
        bal = 1 - sum(abs(xp / sum(xp) - 1 / n)) / (2 * (n - 1) / n)
        return bal

    @staticmethod
    def compute_price_depth(pool_interface, size=0.001):
        combos = pool_interface.base_index_combos

        LD = []
        for i, j in combos:
            ld = pool_interface.get_liquidity_density(i, j)
            LD.append(ld)
        return LD


def format_results(results, parameters, timestamps):
    (
        xs,
        ps,
        pool_balance,
        pool_value,
        price_depth,
        price_error,
        volume,
    ) = results

    param_tuples = [tuple(p.values()) for p in parameters]
    names = list(parameters[0].keys())
    p_list = MultiIndex.from_tuples(param_tuples, names=names)

    x = DataFrame(xs, index=p_list, columns=timestamps)
    p = DataFrame(ps, index=p_list, columns=timestamps)
    err = DataFrame(price_error, index=p_list, columns=timestamps)
    bal = DataFrame(pool_balance, index=p_list, columns=timestamps)
    pool_value = DataFrame(pool_value, index=p_list, columns=timestamps)
    depth = DataFrame(price_depth, index=p_list, columns=timestamps)
    volume = DataFrame(volume, index=p_list, columns=timestamps)
    log_returns = DataFrame(log(pool_value).diff(axis=1).iloc[:, 1:])

    try:
        freq = timestamps.freq / timedelta(minutes=1)
    except Exception:
        print("Warning: assuming 30 minute sampling for annualizing returns")
        freq = 30
    yearmult = 60 / freq * 24 * 365
    ar = DataFrame(exp(log_returns.mean(axis=1) * yearmult) - 1)

    res = {
        "ar": ar,
        "bal": bal,
        "pool_value": pool_value,
        "depth": depth,
        "volume": volume,
        "log_returns": log_returns,
        "err": err,
        "x": x,
        "p": p,
    }

    return res


# Optimizers
def opt_arb(get_bounds, error_function, i, j, p):
    """
    Estimates trade to optimally arbitrage coin[i]
    for coin[j] given external price p (base: i, quote: j)
    p must be less than dy[j]/dx[i], including fees

    Returns:
    trade: format (i,j,dx)
    errors: price errors, (dy-fee)/dx - p,
    for each pair of coins after the trades
    res: output from numerical estimator

    """
    bounds = get_bounds(i, j)
    res = root_scalar(error_function, args=(i, j, p), bracket=bounds, method="brentq")

    trade = (i, j, int(res.root))
    error = error_function(int(res.root), i, j, p)

    return trade, error, res


def opt_arb_multi(pool_interface, prices, limits):  # noqa: C901
    """
    Estimates trades to optimally arbitrage all coins
    in a pool, given prices and volume limits

    Returns:
    trades: list of trades with format (i,j,dx)
    error: (dy-fee)/dx - p
    res: output from numerical estimator

    """
    get_bounds, error_function, error_function_multi = pool_interface.make_error_fns()
    x0, lo, hi, coins, price_targets = get_trade_args(
        pool_interface.price,
        get_bounds,
        error_function,
        prices,
        limits,
        pool_interface.index_combos,
    )

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

        for k in range(len(dxs)):
            if isnan(dxs[k]):
                dx = 0
            else:
                dx = int(dxs[k])

            if dx > 0:
                i = coins[k][0]
                j = coins[k][1]
                trades.append((i, j, dx))

        errors = res.fun

    except Exception:
        print(traceback.format_exc())
        print(
            "Optarbs args:\n",
            "x0: ",
            str(x0),
            "lo: ",
            str(lo),
            "hi: ",
            str(hi),
            "prices: ",
            str(price_targets),
            end="\n" * 2,
        )

        errors = array(error_function_multi([0] * len(x0), price_targets, coins))
        res = []

    return trades, errors, res


def get_trade_args(get_pool_price, get_bounds, error_function, prices, limits, combos):
    x0 = []
    lo = []
    hi = []
    coins = []
    price_targs = []

    for k, pair in enumerate(combos):
        i, j = pair
        lo.append(0)
        hi.append(int(limits[k] * 10**18) + 1)

        if get_pool_price(i, j) - prices[k] > 0:
            try:
                trade, _, _ = opt_arb(get_bounds, error_function, i, j, prices[k])
                x0.append(min(trade[2], int(limits[k] * 10**18)))
            except ValueError:
                print(
                    "Warning: Opt_arb error,",
                    "Pair:",
                    (i, j),
                    "Pool price:",
                    get_pool_price(i, j),
                    "Target Price:",
                    prices[k],
                    "Diff:",
                    get_pool_price(i, j) - prices[k],
                )
                x0.append(0)

            coins.append((i, j))
            price_targs.append(prices[k])

        elif get_pool_price(j, i) - 1 / prices[k] > 0:
            try:
                trade, error, res = opt_arb(
                    get_bounds, error_function, j, i, 1 / prices[k]
                )
                x0.append(min(trade[2], int(limits[k] * 10**18)))
            except ValueError:
                print(
                    "Warning: Opt_arb error,",
                    "Pair:",
                    (j, i),
                    "Pool price:",
                    get_pool_price(j, i),
                    "Target Price:",
                    1 / prices[k],
                    "Diff:",
                    get_pool_price(j, i) - 1 / prices[k],
                )
                x0.append(0)

            coins.append((j, i))
            price_targs.append(1 / prices[k])

        else:
            x0.append(0)
            coins.append((i, j))
            price_targs.append(prices[k])

    # Order trades in terms of expected size
    order = sorted(range(len(x0)), reverse=True, key=x0.__getitem__)
    x0 = [x0[i] for i in order]
    lo = [lo[i] for i in order]
    hi = [hi[i] for i in order]
    coins = [coins[i] for i in order]
    price_targs = [price_targs[i] for i in order]

    return x0, lo, hi, coins, price_targs
