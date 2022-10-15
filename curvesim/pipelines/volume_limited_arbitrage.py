import traceback
from functools import partial
from itertools import combinations

from numpy import array, isnan, linspace
from scipy.optimize import least_squares, root_scalar

from ..iterators.param_samplers import Grid
from ..iterators.price_samplers import PriceVolume
from ..pool.metapool import MetaPool
from ..pool.pool import Pool
from .utils import compute_volume_multipliers

DEFAULT_PARAMS = {
    "A": 2 ** (array(range(12, 28)) / 2),
    "fee": linspace(0.0002, 0.0006, 5) * 10**10,
}

TEST_PARAMS = {"A": array([100, 1000]), "fee": array([0.0003, 0.0004]) * 10**10}


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
):
    pool = pool_data.pool
    coins = pool_data.coins

    if test:
        variable_params = TEST_PARAMS

    param_sampler = Grid(pool, variable_params, fixed_params=fixed_params)
    price_sampler = PriceVolume(coins, days=days, data_dir=data_dir, src=src)

    vol_args = (
        pool_data.volume(days=days),
        price_sampler.total_volumes(),
        pool_data.n(),
        pool_data.type(),
    )

    vol_mult = vol_mult or compute_volume_multipliers(*vol_args, mode=vol_mode)

    results = []
    for _pool in param_sampler:
        # have param_sampler return _pool, params
        symbol = _pool.metadata["symbol"]
        param_str = f"A: {_pool.A}, fee: {_pool.fee}"
        print(f"[{symbol}] Simulating with {param_str}")
        metrics = strategy(_pool, price_sampler.restart(), vol_mult)
        results.append(metrics)

    # param_grid = param_sampler.param_grid
    # timestamps = price_sampler.prices.index
    # results = Results(param_grid, timestamps, metrics)
    # save/show plots
    return results


# Strategy
def strategy(pool, price_sampler, vol_mult):
    trader = Arbitrageur(pool)
    metrics = Metrics()

    for prices, volumes in price_sampler:
        limits = volumes * vol_mult
        trades, errors, res = trader.compute_trades(prices, limits)
        trades_done, volume = trader.do_trades(trades)
        metrics.update(trader.pool, errors, volume)

    return metrics()


class Arbitrageur:
    def __init__(self, pool):
        self.pool = pool

        if isinstance(pool, Pool):
            self.pool.ismeta = False
            self.pool.exchange_fn = self.pool.exchange
            self.pool.price_fn = self.pool.dydxfee

        elif isinstance(pool, MetaPool):
            self.pool.ismeta = True
            self.pool.exchange_fn = self.pool.exchange_underlying
            self.pool.price_fn = self.pool.dydxfee

    def compute_trades(self, prices, volume_limits):
        trades, errors, res = opt_arb_multi(self.pool, prices, volume_limits)
        return trades, errors, res

    def do_trades(self, trades):
        if len(trades) == 0:
            return [], 0

        if self.pool.ismeta:
            p = self.pool.p[0 : self.max_coin] + self.pool.basepool.p[:]
        else:
            p = self.pool.p[:]

        volume = 0
        trades_done = []
        for trade in trades:
            i, j, dx = trade
            dy, dy_fee = self.pool.exchange_fn(i, j, dx)
            trades_done.append(trade + (dy,))

            if self.pool.ismeta:
                if i < self.max_coin or j < self.max_coin:
                    volume += dx * p[i] // 10**18  # in D units
            else:
                volume += dx * p[i] // 10**18  # in D units

        return trades_done, volume


# Metrics
class Metrics:
    xs = []
    ps = []
    pool_balance = []
    pool_value = []
    price_depth = []
    price_error = []
    volume = []

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

        # need to compute ar, etc.
        # return so easily made into DF

        return records

    def update(self, pool, errors, trade_volume):
        if pool.ismeta:
            xp = pool._xp()
            _ps = pool.rates()
        else:
            xp = pool.xp()
            _ps = pool.p[:]

        bal = self.compute_balance(xp, pool.n)
        price_depth = self.compute_price_depth(pool)
        value = pool.get_D(xp, pool.A) / 10**18

        self.xs.append(pool.x[:])
        self.ps.append(_ps)
        self.pool_balance.append(bal)
        self.pool_value.append(value)
        self.price_depth.append(sum(price_depth) / 2)
        self.price_error.append(sum(abs(errors)))
        self.volume.append(trade_volume / 10**18)

    @staticmethod
    def compute_balance(xp, n):
        xp = array(xp)
        bal = 1 - sum(abs(xp / sum(xp) - 1 / n)) / (2 * (n - 1) / n)
        return bal

    @staticmethod
    def compute_price_depth(pool, size=0.001):
        combos = list(combinations(range(pool.n), 2))

        if pool.ismeta:
            xp = pool._xp()
            sumxp = sum(xp)
            pool.exchange_fn = pool.exchange
            pool.price_fn = partial(pool._dydx, xp, use_fee=True)
        else:
            sumxp = sum(pool.xp())

        depth = []
        for i, j in combos:
            p = pool.price_fn(i, j) * (1 - size)
            trade, _, _ = opt_arb(pool, i, j, p)
            depth.append(trade[2] / sumxp)

            p = pool.price_fn(j, i) * (1 - size)
            trade, _, _ = opt_arb(pool, j, i, p)
            depth.append(trade[2] / sumxp)

        if pool.ismeta:
            pool.exchange_fn = pool.exchange_underlying
            pool.price_fn = pool.dydxfee

        return depth


# Optimizers
def opt_arb(pool, i, j, p):
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
    if pool.ismeta:
        # Use base_i or base_j if they are >= 0
        base_i = i - pool.max_coin
        base_j = j - pool.max_coin
        meta_i = pool.max_coin
        meta_j = pool.max_coin
        if base_i < 0:
            meta_i = i
        if base_j < 0:
            meta_j = j

        if base_i < 0 or base_j < 0:
            rates = pool.rates()
            xp = [x * p // 10**18 for x, p in zip(pool.x, rates)]
            hi = pool.get_y(meta_j, meta_i, int(xp[meta_j] * 0.01), xp) - xp[meta_i]

        else:
            base_xp = pool.basepool.xp()
            hi = (
                pool.basepool.get_y(
                    base_j, base_i, int(base_xp[base_j] * 0.01), base_xp
                )
                - base_xp[base_i]
            )

        bounds = (1, hi)

    else:
        xp = pool.xp()
        bounds = (
            1,
            pool.get_y(j, i, int(xp[j] * 0.01), xp) - xp[i],
        )  # Lo: 1, Hi: enough coin[i] to leave 1% of coin[j]

    res = root_scalar(
        price_error, args=(pool, i, j, p), bracket=bounds, method="brentq"
    )

    trade = (i, j, int(res.root))

    error = price_error(int(res.root), pool, i, j, p)

    return trade, error, res


def opt_arb_multi(pool, prices, limits):  # noqa: C901
    """
    Estimates trades to optimally arbitrage all coins
    in a pool, given prices and volume limits

    Returns:
    trades: list of trades with format (i,j,dx)
    error: (dy-fee)/dx - p
    res: output from numerical estimator

    """
    combos = list(combinations(range(pool.n_total), 2))

    # Initial guesses for dx, limits, and trades
    # uses opt_arb (i.e., only considering price of coin[i] and coin[j])
    # guess will be too high but in range
    x0 = []
    lo = []
    hi = []
    coins = []
    price_targs = []

    for k, pair in enumerate(combos):
        i, j = pair

        if pool.dydxfee(i, j) - prices[k] > 0:
            try:
                trade, error, res = opt_arb(pool, i, j, prices[k])
                x0.append(min(trade[2], int(limits[k] * 10**18)))
            except Exception:
                x0.append(0)

            lo.append(0)
            hi.append(int(limits[k] * 10**18) + 1)
            coins.append((i, j))
            price_targs.append(prices[k])

        elif pool.dydxfee(j, i) - 1 / prices[k] > 0:
            try:
                trade, error, res = opt_arb(pool, j, i, 1 / prices[k])
                x0.append(min(trade[2], int(limits[k] * 10**18)))
            except Exception:
                x0.append(0)

            lo.append(0)
            hi.append(int(limits[k] * 10**18) + 1)
            coins.append((j, i))
            price_targs.append(1 / prices[k])

        else:
            x0.append(0)
            lo.append(0)
            hi.append(int(limits[k] * 10**18 + 1))
            coins.append((i, j))
            price_targs.append(prices[k])

    # Order trades in terms of expected size
    order = sorted(range(len(x0)), reverse=True, key=x0.__getitem__)
    x0 = [x0[i] for i in order]
    lo = [lo[i] for i in order]
    hi = [hi[i] for i in order]
    coins = [coins[i] for i in order]
    price_targs = [price_targs[i] for i in order]

    # Find trades that minimize difference between
    # pool price and external market price
    trades = []
    try:
        res = least_squares(
            price_error_multi,
            x0=x0,
            args=(pool, price_targs, coins),
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
            "Optarbs args:\n"
            + "x0: "
            + str(x0)
            + ", lo: "
            + str(lo)
            + ", hi: "
            + str(hi)
            + ", prices: "
            + str(price_targs),
            end="\n" * 2,
        )

        errors = array(price_error_multi([0] * len(x0), pool, price_targs, coins))

        res = []

    return trades, errors, res


# Error functions for optimizers
def price_error(dx, pool, i, j, p):
    if pool.ismeta and i >= pool.max_coin:
        base_i = i - pool.max_coin
        rate = pool.basepool.p[base_i]
    else:
        rate = pool.p[i]
    dx = int(dx) * 10**18 // rate

    x_old = pool.x[:]
    if pool.ismeta:
        x_old_base = pool.basepool.x[:]
        tokens_old = pool.basepool.tokens

    pool.exchange_fn(i, j, dx)  # do trade

    # Check price error after trade
    # Error = pool price (dy/dx) - external price (p);
    error = pool.price_fn(i, j) - p

    pool.x = x_old
    if pool.ismeta:
        pool.basepool.x = x_old_base
        pool.basepool.tokens = tokens_old

    return error


def price_error_multi(dxs, pool, price_targs, coins):
    rates = pool.p[:]
    x_old = pool.x[:]

    if pool.ismeta:
        x_old_base = pool.basepool.x[:]
        tokens_old = pool.basepool.tokens
        rates.pop()
        rates.extend(pool.basepool.p)

    # Do each trade
    for k, pair in enumerate(coins):
        i, j = pair

        if isnan(dxs[k]):
            dx = 0
        else:
            dx = int(dxs[k]) * 10**18 // rates[i]

        if dx > 0:
            pool.exchange_fn(i, j, dx)

    # Check price errors after all trades
    errors = []
    for k, pair in enumerate(coins):
        p = price_targs[k]
        errors.append(pool.price_fn(*pair) - p)

    pool.x = x_old
    if pool.ismeta:
        pool.basepool.x = x_old_base
        pool.basepool.tokens = tokens_old

    return errors
