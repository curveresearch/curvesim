import multiprocessing
from datetime import datetime, timedelta
from functools import partial
from itertools import combinations, product
from math import factorial

import numpy as np
import pandas as pd

from curvesim.network import coingecko, nomics
from curvesim.plot import plotsims, plotsimsfee, saveplots
from curvesim.pool import Pool
from curvesim.pool_data import get


def sim(A, D, n, fee, prices, volumes, tokens=None, fee_mul=None, vol_mult=1, r=None):
    """
    Simulates a pool with parameters A, D, n, and fee, given time series of prices and volumes

    A: amplitude parameter, technically A*n**(n - 1), as in the pool contracts
    D: Total deposit size, precision 10**18
    n: number of currencies; if list, assumes meta-pool
    fee: fee with precision 10**10. Default fee is .0004 (.04%)
    prices: time series of pairwise prices
    volumes: time series of pairwise exchange volumes

    tokens: # of tokens; if meta-pool, this sets # of basepool tokens
    fee_mul: fee multiplier for dynamic fee pools
    vol_mult: scalar or vector (one element per pair) multiplied by market volume to limit trade sizes
    r: time series of redemption prices for RAI-like pools

    Returns:
    pl: pool object at end of simulation
    err: time series of absolute price errors, (dy-fee)/dx - p, summed accros coin pairs
    bal: balance parameter over time; bal=1 when in perfect balance, and bal=0 when all holdings are in 1 coin
    pool_value: time series of pool's value (based on virtual price)
    depth: time series of price depth, averaged across pool's coin; see pricedepth()
    volume: time series of pool volume
    xs: time series of pool holdings
    ps: time series of pool precisions (incl. basepool virtual price and/or RAI redemption price)

    """

    print("Simulating A=" + str(A) + ", Fee=" + str(np.array(fee) / int(10**8)) + "%")

    if r is not None:
        r = r.reindex(prices.index, method="ffill")
        r0 = int(r.price[0])
    else:
        r0 = None

    # Initiate pool
    pl = Pool(A, D, n, fee=fee, tokens=tokens, fee_mul=fee_mul, r=r0)

    # Loop through timepoints and do optimal arb trades
    err = []
    bal = []
    pool_value = []
    depth = []
    volume = []
    xs = []
    ps = []

    for t in range(len(prices)):
        curr_prices = prices.iloc[t]
        curr_volume = volumes.iloc[t] * vol_mult
        if r is not None:
            pl.p[0] = int(r.price[t])  # update redemption price if needed

        trades, errors, res = pl.optarbs(curr_prices, curr_volume)
        if len(trades) > 0:
            trades_done, trade_volume = pl.dotrades(trades)
            volume.append(trade_volume / 10**18)
        else:
            volume.append(0)

        err.append(sum(abs(errors)))
        depth.append(np.sum(pl.pricedepth()) / 2)

        if pl.ismeta:
            # Pool Value
            rates = pl.p[:]
            rates[pl.max_coin] = pl.basepool.get_virtual_price()
            if r0 is not None:
                rates[pl.max_coin - 1] = r0  # value pool with redemption price held constant
            xp = [x * p // 10**18 for x, p in zip(pl.x, rates)]
            pool_value.append(pl.D(xp=xp))

            # Balance
            if r0 is not None:
                rates[pl.max_coin - 1] = int(r.price[t])  # compute balance with current redemption price
                xp = [x * p // 10**18 for x, p in zip(pl.x, rates)]
            xp = np.array(xp)
            bal.append(1 - sum(abs(xp / sum(xp) - 1 / n[0])) / (2 * (n[0] - 1) / n[0]))
            ps.append(rates)
        else:
            xp = np.array(pl.xp())
            pool_value.append(pl.D())
            bal.append(1 - sum(abs(xp / sum(xp) - 1 / n)) / (2 * (n - 1) / n))
            ps.append(pl.p[:])

        xs.append(pl.x[:])

    pool_value = np.array(pool_value).astype(float) / 10**18
    return pl, err, bal, pool_value, depth, volume, xs, ps


def psim(
    A_list,
    D,
    n,
    fee_list,
    prices,
    volumes,
    A_base=None,
    fee_base=None,
    tokens=None,
    fee_mul=None,
    vol_mult=1,
    r=None,
    plot=False,
    ncpu=4,
):
    """
    Calls sim() with a variety of A parameters (A_list) and/or fees (fee_list)
    Parallelized using multiprocessing starmap()

    A_list: list of A values
    D: Total deposit size, precision 10**18
    n: number of currencies; if list, assumes meta-pool
    fee_list: list of fees with precision 10**10
    prices: time series of pairwise prices
    volumes: time series of pairwise exchange volumes

    A_base: if metapool, A parameter for basepool
    fee_base: if metapool, fee for basepool
    tokens: # of tokens; if meta-pool, this sets # of basepool tokens
    fee_mul: fee multiplier for dynamic fee pools
    vol_mult: scalar or vector (one element per pair) multiplied by market volume to limit trade sizes
    r: time series of redemption prices for RAI-like pools
    plot: if true, plots outputs
    ncpu: number of CPUs to use for parallel processing


    Returns a dict containing:
    ar: annualized returns
    bal: balance parameter over time; bal=1 when in perfect balance, and bal=0 when all holdings are in 1 coin
    pool_value: time series of pool's value (based on virtual price)
    depth: time series of price depth, averaged across pool's coin; see pricedepth()
    volume: time series of pool volume
    log_returns: log returns over time
    err: time series of absolute price errors, (dy-fee)/dx - p, summed accros coin pairs
    x: time series of pool holdings
    p: time series of pool precisions (incl. basepool virtual price and/or RAI redemption price)

    """

    # Format inputs
    A_list = [int(round(A)) for A in A_list]
    fee_list = [int(round(fee)) for fee in fee_list]
    A_list_orig = A_list
    fee_list_orig = fee_list

    p_list = list(product(A_list, fee_list))

    if A_base is not None:
        A_list = [[A, A_base] for A in A_list]

    if fee_base is not None:
        fee_list = [[fee, fee_base] for fee in fee_list]

    # Run sims
    simmapfunc = partial(sim, tokens=tokens, fee_mul=fee_mul, vol_mult=vol_mult, r=r)
    if ncpu > 1:
        with multiprocessing.Pool(ncpu) as clust:
            pl, err, bal, pool_value, depth, volume, xs, ps = zip(
                *clust.starmap(
                    simmapfunc,
                    [(A, D, n, fee, prices, volumes) for A in A_list for fee in fee_list],
                )
            )
    else:
        params_list = zip(*[(A, D, n, fee, prices, volumes) for A in A_list for fee in fee_list])
        pl, err, bal, pool_value, depth, volume, xs, ps = zip(*map(simmapfunc, *params_list))

    # Output as DataFrames
    p_list = pd.MultiIndex.from_tuples(p_list, names=["A", "fee"])

    err = pd.DataFrame(err, index=p_list, columns=prices.index)
    bal = pd.DataFrame(bal, index=p_list, columns=prices.index)
    pool_value = pd.DataFrame(pool_value, index=p_list, columns=prices.index)
    depth = pd.DataFrame(depth, index=p_list, columns=prices.index)
    volume = pd.DataFrame(volume, index=p_list, columns=prices.index)

    log_returns = pd.DataFrame(np.log(pool_value).diff(axis=1).iloc[:, 1:])

    try:
        freq = prices.index.freq / timedelta(minutes=1)
    except Exception:
        freq = 30
    yearmult = 60 / freq * 24 * 365
    ar = pd.DataFrame(np.exp(log_returns.mean(axis=1) * yearmult) - 1)

    x = pd.DataFrame(xs, index=p_list, columns=prices.index)
    p = pd.DataFrame(ps, index=p_list, columns=prices.index)

    # Plotting
    if plot:
        if len(fee_list) > 1:
            plotsimsfee(A_list_orig, fee_list_orig, ar, bal, depth, volume, err)
        else:
            plotsims(A_list_orig, ar, bal, pool_value, depth, volume, log_returns, err)

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


def autosim(  # noqa: C901
    poolname,
    chain="mainnet",
    test=False,
    A=None,
    D=None,
    fee=None,
    vol_mult=None,
    vol_mode=1,
    fee_mul=None,
    src="cg",
    ncpu=4,
    trunc=None,
    pool_data=None,
    data_dir="data",
):
    """
    Simplified function to simulate existing Curve pools.
    Fetches pool state and 2-months price data, runs psim, and saves results images to "pools" directory.

    Requires an entry for "poolname" in poolDF.csv

    A, D, fee, vol_mult, & fee_mul can be used to override default values and/or fetched data.
    D & fee should be provided in "natural" units (i.e., not 10**18 or 10**10 precision).
    A & fee must be lists/np.arrays.

    If test==True, uses a limited number of A/fee values

    vol_mode: chooses method for estimating vol_mult (i.e., trade volume limiter)
        -1: limits trade volumes proportionally to market volume for each pair
        -2: limits trade volumes equally across pairs
        -3: mode 2 for trades with meta-pool asset, mode 1 for basepool-only trades

    src: chooses data source
        -'cg': CoinGecko (free)
        -'nomics': nomics (requires paid API key in nomics.py)
        -'local': pulls from CSVs in "data" folder

    ncpu: number of CPUs to use for parallel processing
    trunc: truncate price/volume data to [trunc[0]:trunc[1]]

    Returns results dict from psim
    """

    # Get current pool data
    print("[" + poolname + "] Fetching pool data...")

    pldata = pool_data or get(poolname, chain)

    histvolume = pldata["histvolume"]
    coins = pldata["coins"]
    n = pldata["n"]

    # Over-ride D & fee_mul if necessary
    if D is None:
        D = pldata["D"]
    else:
        D = int(D * 10**18)
        if isinstance(pldata["D"], list):  # if metapool
            pldata["D"][0] = D
            D = pldata["D"]

    if fee_mul is None:
        fee_mul = pldata["fee_mul"]

    # Update and load price data
    if src == "nomics":
        print("[" + poolname + "] Fetching Nomics price data...")
        # update CSVs
        t_end = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        t_start = t_end - timedelta(days=60)
        print("Timerange: %s to %s" % (str(t_start), str(t_end)))
        nomics.update(coins, None, t_start, t_end)

        # Load data
        prices, volumes, pzero = nomics.pool_prices(coins)

    elif src == "local":
        print("[" + poolname + "] Fetching local price data...")
        prices, volumes, pzero = nomics.pool_prices(coins, data_dir=data_dir)

    elif src == "cg":
        print("[" + poolname + "] Fetching CoinGecko price data...")
        prices, volumes = coingecko.pool_prices(coins, "usd", 60)

    # Truncate data if needed
    if trunc is not None:
        prices = prices[trunc[0] : trunc[1]]
        volumes = volumes[trunc[0] : trunc[1]]

    # Calculate volume multiplier
    if vol_mult is None:
        if isinstance(n, list):  # is metapool
            n_base_pairs = int(factorial(n[1]) / 2 * factorial(n[1] - 2))
            if vol_mode == 1:
                vol_mult = histvolume[0] / volumes.sum()[0 : n[1]].sum().repeat(
                    n[1]
                )  # trades including meta-pool coin
                vol_mult = np.append(
                    vol_mult, histvolume[1] / volumes.sum()[n[1] :].sum().repeat(n_base_pairs)
                )  # basepool trades
            elif vol_mode == 2:
                vol_mult = histvolume[0].repeat(n[1]) / n[1] / volumes.sum()[0 : n[1]]
                vol_mult = np.append(
                    vol_mult, histvolume[1].repeat(n_base_pairs) / n_base_pairs / volumes.sum()[n[1] :]
                )
            elif vol_mode == 3:
                vol_mult = histvolume[0].repeat(n[1]) / n[1] / volumes.sum()[0 : n[1]]
                vol_mult = np.append(
                    vol_mult, histvolume[1] / volumes.sum()[n[1] :].sum().repeat(n_base_pairs)
                )

        else:
            if vol_mode == 1:
                vol_mult = histvolume / volumes.sum().sum()
            if vol_mode == 2:
                sumvol = volumes.sum()
                vol_mult = histvolume.repeat(len(sumvol)) / len(sumvol) / sumvol
            if vol_mode == 3:
                print("Vol_mode=3 only available for meta-pools. Reverting to vol_mode=1")
                vol_mult = histvolume / volumes.sum().sum()
    print("Volume multipliers:")
    print(vol_mult)

    # Default ranges of A and fee values
    if A is None:
        A_list = 2 ** (np.array(range(12, 28)) / 2)
    else:
        A_list = np.array(A)

    if fee is None:
        fee_list = np.linspace(0.0002, 0.0006, 5) * 10**10
    else:
        fee_list = np.array(fee) * 10**10

    # Test values
    if test:
        A_list = np.array([100, 1000])
        fee_list = np.array([0.0003, 0.0004]) * 10**10

    # Run sims
    A_list = [int(round(A)) for A in A_list]
    fee_list = [int(round(fee)) for fee in fee_list]

    res = psim(
        A_list,
        D,
        n,
        fee_list,
        prices,
        volumes,
        A_base=pldata["A_base"],
        fee_base=pldata["fee_base"],
        tokens=pldata["tokens"],
        fee_mul=fee_mul,
        vol_mult=vol_mult,
        r=pldata["r"],
        plot=False,
        ncpu=ncpu,
    )

    # Save plots
    saveplots(
        poolname,
        A_list,
        fee_list,
        res["ar"],
        res["bal"],
        res["depth"],
        res["volume"],
        res["pool_value"],
        res["log_returns"],
        res["err"],
    )

    # Save text
    combos = list(combinations(coins, 2))
    startstr = prices.index[0].strftime("%m/%d/%y")
    endstr = prices.index[-1].strftime("%m/%d/%y")
    txt = "Simulation period: " + startstr + " to " + endstr

    if src == "cg":
        ps = "CAUTION: Trade volume limiting may be less accurate for CoinGecko data."
    else:
        ps = "Data Availability:\n"
        for i in range(len(pzero)):
            ps += combos[i][0] + "/" + combos[i][1] + ": " + str(round((1 - pzero[i]) * 1000) / 10) + "%\n"

        if any(pzero > 0.3):
            ps += "CAUTION: Limited price data used in simulation"

    filename = "results/" + poolname + "/pooltext.txt"
    with open(filename, "w") as txt_file:
        txt_file.write(txt + "\n")
        txt_file.write(ps)

    return res
