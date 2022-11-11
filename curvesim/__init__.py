"""Package to simulate Curve pool."""
__all__ = ["autosim", "__version__", "__version_info__"]

from itertools import combinations as _combinations

from numpy import linspace as _linspace
from pandas import DataFrame

from curvesim import plot, pool

from .sim import autosim
from .version import __version__, __version_info__


def orderbook(pool_obj, i, j, width=0.1, resolution=10**23, use_fee=True, show=True):
    """
    Computes and optionally plots an orderbook representation of exchange rates
    between two tokens.

    Parameters
    ----------
    pool_obj : CurvePool or CurveMetaPool
        A pool object to compute the bonding curve for.

    i : int
        The index of the "base" token to compute exchange rates for.
        To index the basepool token, use "bp_token"

    j : int
        The index of the "quote" token traded against.
        To index the basepool token, use "bp_token"

    width: float, default=0.1
        The width of the orderbook to compute
        (i.e., from price*(1-width) to price*(1+width))

    resolution : int, default=10**23
        The trade-size interval between points in the orderbook (18-decimal precision)

    use_fee : bool, default=True
        If True, includes fees when computing the orderbook.

    show : bool, default=True
        If true, plots the bonding curve.

    Returns
    -------
    bids : pandas.DataFrame
        DataFrame of prices and depths for each point on the "bid" side of the orderbook

    asks : pandas.DataFrame
        DataFrame of prices and depths for each point on the "ask" side of the orderbook

    """

    is_meta = isinstance(pool_obj, pool.CurveMetaPool)

    i, j, functions, state = _orderbook_args(pool_obj, is_meta, i, j)
    get_price, get_xp, exchange = functions
    x0, x0_base, t0_base = state

    # Bids
    depth = 0
    if get_xp:
        xp = get_xp()
        price = get_price(i, j, xp, use_fee=use_fee)
    else:
        price = get_price(i, j, use_fee=use_fee)

    bids = [(price, depth)]

    while bids[-1][0] > bids[0][0] * (1 - width):
        depth += resolution
        dy, fee = exchange(i, j, depth)

        if get_xp:
            xp = get_xp()
            price = get_price(i, j, xp, use_fee=use_fee)
        else:
            price = get_price(i, j, use_fee=use_fee)

        bids.append((price, depth / 10**18))

        # Return to initial state
        pool_obj.x = x0[:]
        if is_meta:
            pool_obj.basepool.x = x0_base[:]
            pool_obj.basepool.tokens = t0_base

    # Asks
    depth = 0
    if get_xp:
        xp = get_xp()
        price = get_price(j, i, xp, use_fee=use_fee)
    else:
        price = get_price(j, i, use_fee=use_fee)

    asks = [(1 / price, depth)]

    while asks[-1][0] < asks[0][0] * (1 + width):
        depth += resolution
        dy, fee = exchange(j, i, depth)

        if get_xp:
            xp = get_xp()
            price = get_price(j, i, xp, use_fee=use_fee)
        else:
            price = get_price(j, i, use_fee=use_fee)

        asks.append((1 / price, dy / 10**18))

        # Return to initial state
        pool_obj.x = x0[:]
        if is_meta:
            pool_obj.basepool.x = x0_base[:]
            pool_obj.basepool.tokens = t0_base

    # Format DataFrames
    bids = DataFrame(bids, columns=["price", "depth"]).set_index("price")
    asks = DataFrame(asks, columns=["price", "depth"]).set_index("price")

    if show:
        plot.plt.plot(bids, color="red")
        plot.plt.plot(asks, color="green")
        plot.plt.xlabel("Price")
        plot.plt.ylabel("Depth")
        plot.plt.show()

    return bids, asks


def _orderbook_args(pool_obj, is_meta, i, j):
    if is_meta:
        # Store initial state
        x0 = pool_obj.x[:]
        x0_base = pool_obj.basepool.x[:]
        t0_base = pool_obj.basepool.tokens

        # Set functions/parameters
        get_price = pool_obj.dydx
        exchange = pool_obj.exchange_underlying
        get_xp = False

        if i == "bp_token":
            i = pool_obj.max_coin
            get_price = pool_obj._dydx
            exchange = pool_obj.exchange
            get_xp = pool_obj._xp

        if j == "bp_token":
            j = pool_obj.max_coin
            get_price = pool_obj._dydx
            exchange = pool_obj.exchange
            get_xp = pool_obj._xp

    else:
        x0 = pool_obj.x[:]
        x0_base = None
        t0_base = None
        get_price = pool_obj.dydx
        exchange = pool_obj.exchange
        get_xp = False

    return i, j, (get_price, get_xp, exchange), (x0, x0_base, t0_base)


def bonding_curve(pool_obj, truncate=0.0001, resolution=1000, show=True):
    """
    Computes and optionally plots a pool's bonding curve and current reserves.

    Parameters
    ----------
    pool_obj : CurvePool or CurveMetaPool
        A pool object to compute the bonding curve for.

    truncate : float, default=0.0001
        Determines where to truncate the bonding curve (i.e., D*truncate).

    resolution : int, default=1000
        Number of points along the bonding curve to compute.

    show : bool, default=True
        If true, plots the bonding curve.

    Returns
    -------
    xs : list of lists
        Lists of reserves for the first coin in each combination of token pairs

    ys : list of lists
        Lists of reserves for the second coin in each combination of token pairs

    """

    if isinstance(pool_obj, pool.CurveMetaPool):
        combos = [(0, 1)]
    else:
        combos = list(_combinations(range(pool_obj.n), 2))

    try:
        labels = pool_obj.metadata["coins"]["names"]
    except (AttributeError, KeyError):
        labels = [f"Coin {str(label)}" for label in range(pool_obj.n)]

    if show:
        _, axs = plot.plt.subplots(1, len(combos), constrained_layout=True)

    D = pool_obj.D()
    xp = pool_obj._xp()

    xs_out = []
    ys_out = []
    for n, combo in enumerate(combos):
        i, j = combo

        xs_n = _linspace(
            int(D * truncate), pool_obj.get_y(j, i, D * truncate, xp), resolution
        ).round()

        ys_n = []
        for x in xs_n:
            ys_n.append(pool_obj.get_y(i, j, int(x), xp))

        xs_n = [x / 10**18 for x in xs_n]
        ys_n = [y / 10**18 for y in ys_n]
        xs_out.append(xs_n)
        ys_out.append(ys_n)

        if show:
            if len(combos) == 1:
                ax = axs
            else:
                ax = axs[n]

            ax.plot(xs_n, ys_n, color="black")
            ax.scatter(xp[i] / 10**18, xp[j] / 10**18, s=40, color="black")
            ax.set_xlabel(labels[i])
            ax.set_ylabel(labels[j])

    if show:
        plot.plt.show()

    return xs_out, ys_out
