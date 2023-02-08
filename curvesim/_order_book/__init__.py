"""
Contains order_book function for computing and optionally plotting orderbook
representations of exchange rates between two tokens.
"""

import matplotlib.pyplot as plt
from pandas import DataFrame

from curvesim.pool import CurveMetaPool


def order_book(pool, i, j, *, width=0.1, resolution=10**23, use_fee=True, show=True):
    """
    Computes and optionally plots an orderbook representation of exchange rates
    between two tokens.

    Parameters
    ----------
    pool : CurvePool or CurveMetaPool
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
    snapshot = pool.get_snapshot()
    i, j, functions = _orderbook_args(pool, i, j)
    get_price, exchange = functions

    # Bids
    depth = 0
    price = get_price(i, j, use_fee=use_fee)

    bids = [(price, depth)]

    while bids[-1][0] > bids[0][0] * (1 - width):
        depth += resolution

        dy, _ = exchange(i, j, depth)
        price = get_price(i, j, use_fee=use_fee)

        bids.append((price, depth / 10**18))

        # Return to initial state
        pool.revert_to_snapshot(snapshot)

    # Asks
    depth = 0
    price = get_price(j, i, use_fee=use_fee)

    asks = [(1 / price, depth)]

    while asks[-1][0] < asks[0][0] * (1 + width):
        depth += resolution
        dy, _ = exchange(j, i, depth)
        price = get_price(j, i, use_fee=use_fee)

        asks.append((1 / price, dy / 10**18))

        # Return to initial state
        pool.revert_to_snapshot(snapshot)

    # Format DataFrames
    bids = DataFrame(bids, columns=["price", "depth"]).set_index("price")
    asks = DataFrame(asks, columns=["price", "depth"]).set_index("price")

    if show:
        plt.plot(bids, color="red")
        plt.plot(asks, color="green")
        plt.xlabel("Price")
        plt.ylabel("Depth")
        plt.show()

    return bids, asks


def _orderbook_args(pool, i, j):
    if isinstance(pool, CurveMetaPool):
        # Set functions/parameters
        get_price = pool.dydx
        exchange = pool.exchange_underlying

        # Price function closure if bp_token used
        def get_meta_price(i, j, use_fee):
            # pylint: disable=protected-access
            xp = pool._xp()
            price = pool._dydx(i, j, xp, use_fee=use_fee)
            return price

        if i == "bp_token":
            i = pool.max_coin
            get_price = get_meta_price
            exchange = pool.exchange

        if j == "bp_token":
            j = pool.max_coin
            get_price = get_meta_price
            exchange = pool.exchange

    else:
        get_price = pool.dydx
        exchange = pool.exchange

    return i, j, (get_price, exchange)
