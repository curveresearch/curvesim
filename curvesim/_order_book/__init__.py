"""
Contains order_book function for computing and optionally plotting orderbook
representations of exchange rates between two tokens.
"""

import matplotlib.pyplot as plt
from pandas import DataFrame

from ..pool import CurveMetaPool


def order_book(
    pool_obj, i, j, *, width=0.1, resolution=10**23, use_fee=True, show=True
):
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

    is_meta = isinstance(pool_obj, CurveMetaPool)

    i, j, functions, pre_trade_state = _orderbook_args(pool_obj, is_meta, i, j)
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
        pool_obj.x = pre_trade_state["x0"][:]
        if is_meta:
            pool_obj.basepool.x = pre_trade_state["x0_base"][:]
            pool_obj.basepool.tokens = pre_trade_state["t0_base"]

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
        pool_obj.x = pre_trade_state["x0"][:]
        if is_meta:
            pool_obj.basepool.x = pre_trade_state["x0_base"][:]
            pool_obj.basepool.tokens = pre_trade_state["t0_base"]

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


def _orderbook_args(pool_obj, is_meta, i, j):
    if is_meta:

        # Store initial state
        pre_trade_state = {
            "x0": pool_obj.x[:],
            "x0_base": pool_obj.basepool.x[:],
            "t0_base": pool_obj.basepool.tokens,
        }

        # Set functions/parameters
        get_price = pool_obj.dydx
        exchange = pool_obj.exchange_underlying

        # Price function closure if bp_token used
        def get_meta_price(i, j, use_fee):
            xp = pool_obj._xp()
            price = pool_obj._dydx(i, j, xp, use_fee=use_fee)
            return price

        if i == "bp_token":
            i = pool_obj.max_coin
            get_price = get_meta_price
            exchange = pool_obj.exchange

        if j == "bp_token":
            j = pool_obj.max_coin
            get_price = get_meta_price
            exchange = pool_obj.exchange

    else:
        pre_trade_state = {"x0": pool_obj.x[:]}
        get_price = pool_obj.dydx
        exchange = pool_obj.exchange

    return i, j, (get_price, exchange), pre_trade_state
