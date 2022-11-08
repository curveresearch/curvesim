"""
Network connector for nomics API.
"""
import asyncio
import os
from datetime import timedelta, timezone
from itertools import combinations

import pandas as pd
from dotenv import load_dotenv
from numpy import NaN

from .http import HTTP
from .utils import sync

load_dotenv()
key = os.environ.get("NOMICS_API_KEY")
URL = "https://api.nomics.com/v1/"

FORMAT = "%Y-%m-%dT%H:%M:%SZ"
ETH_addr = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"


async def get_data(url, params, t_start, t_end, exp=1):
    # Chunk times by days
    t_starts, t_ends = chunk_times(t_start, t_end)

    # Get data
    tasks = []
    ps = []
    for i in range(len(t_starts)):
        p = params.copy()
        p["start"] = t_starts[i].strftime(FORMAT)
        p["end"] = t_ends[i].strftime(FORMAT)
        ps.append(p)
        tasks.append(HTTP.get(url, params=ps[i]))

    data = await asyncio.gather(*tasks)
    data = format_price_data(data, t_start, t_end, exp=exp)

    return data


async def get_mkt(market, t_start, t_end):
    # Request parameters
    url = URL + "exchange_candles"
    p = {"key": key, "interval": "30m", "exchange": market[0], "market": market[1]}

    data = await get_data(url, p, t_start, t_end, exp=market[2])

    return data


async def get_agg(coins, t_start, t_end, exp=1):
    # Request parameters
    url = URL + "markets/candles"
    p = {"key": key, "interval": "30m", "base": coins[0], "quote": coins[1]}

    data = await get_data(url, p, t_start, t_end, exp=exp)

    return data


async def vwap_mkt(markets, t_start, t_end):
    prices = []
    volumes = []
    for market in markets:
        data = await get_mkt(market, t_start, t_end)
        prices.append(data["price"])
        volumes.append(data["volume"])

    prices = pd.concat(prices, axis=1)
    volumes = pd.concat(volumes, axis=1)

    # Use NaN for missing data to avoid ZeroDiv
    sum_volume = volumes.sum(1).replace(0, NaN)

    weights = volumes.divide(sum_volume, "index")
    vwap = (prices * weights.values).sum(1)
    sum_volume.fillna(0, inplace=True)

    data = pd.concat([vwap, sum_volume], axis=1)
    data.columns = ["price", "volume"]

    return data


async def vwap_agg(coins, t_start, t_end):
    prices = []
    volumes = []

    data = await asyncio.gather(
        get_agg(coins, t_start, t_end, exp=1),
        get_agg(coins[::-1], t_start, t_end, exp=-1),
    )

    prices = [d["price"] for d in data]
    volumes = [d["volume"] for d in data]

    prices = pd.concat(prices, axis=1)
    volumes = pd.concat(volumes, axis=1)

    # Use NaN for missing data to avoid ZeroDiv
    sum_volume = volumes.sum(1).replace(0, NaN)

    weights = volumes.divide(sum_volume, "index")
    vwap = (prices * weights.values).sum(1)
    sum_volume.fillna(0, inplace=True)

    data = pd.concat([vwap, sum_volume], axis=1)
    data.columns = ["price", "volume"]

    return data


def chunk_times(t_start, t_end):
    # Round times to nearest 30-min interval (floor)
    t_start = t_start.replace(minute=t_start.minute // 30 * 30, second=0, microsecond=0)
    t_end = t_end.replace(minute=t_end.minute // 30 * 30, second=0, microsecond=0)

    # Divide timerange into 1-day chunks
    t_starts = pd.date_range(start=t_start, end=t_end, freq="1d")
    t_ends = t_starts + timedelta(days=1) - timedelta(minutes=30)

    t_starts = t_starts.to_list()
    t_ends = t_ends.to_list()
    t_ends[-1] = t_end  # replace last value with end of total timerange

    return t_starts, t_ends


def format_price_data(data, t_start, t_end, exp=1):
    # Remove empty data
    data = [d for d in data if d]

    if not data:
        data = pd.DataFrame(columns=["price", "volume"])

    else:
        for i in range(len(data)):
            data[i] = pd.DataFrame(data[i])[["timestamp", "close", "volume"]]
            data[i].set_index("timestamp", inplace=True)

        data = pd.concat(data)
        data.columns = ["price", "volume"]

        data.index = pd.to_datetime(data.index)

        # Take reciprocal when base/quote reversed
        data["price"] = pd.to_numeric(data["price"]) ** exp
        if exp == 1:
            data["volume"] = pd.to_numeric(data["volume"])
        elif exp == -1:
            data["volume"] = pd.to_numeric(data["volume"]) / data["price"]

    # Fill in missing data
    t_samples = pd.date_range(start=t_start, end=t_end, freq="30min", tz=timezone.utc)
    data = data.reindex(t_samples)
    data["volume"].fillna(0, inplace=True)
    data["price"].fillna(method="ffill", inplace=True)

    return data


def update(coins, quote, t_start, t_end, pairs=False, data_dir="data"):  # noqa: C901
    t_start = t_start.replace(tzinfo=timezone.utc)
    t_start_orig = t_start
    t_end = t_end.replace(tzinfo=timezone.utc)

    loop = asyncio.get_event_loop()
    coins = coin_ids_from_addresses_sync(coins, event_loop=loop)

    # Coins priced against one another
    if quote is None:
        # Create pairs
        if pairs is False:
            combos = list(combinations(coins, 2))

        # Pairs already provided
        else:
            combos = coins

    # Coins prices against single quote currency
    else:
        quote = coin_ids_from_addresses_sync(quote, event_loop=loop)
        combos = [(coin, quote) for coin in coins]

    # Get data for each pair
    for pair in combos:
        f_name = os.path.join(data_dir, f"{pair[0]}-{pair[1]}.csv")
        vwap_args = None

        try:
            curr_file = pd.read_csv(f_name, index_col=0)
            curr_file.index = pd.to_datetime(curr_file.index)

            if t_start_orig < curr_file.index[-1]:
                t_start = pd.to_datetime(curr_file.index[-1]) + timedelta(minutes=30)
                t_start = t_start.replace(tzinfo=timezone.utc)
            else:
                t_start = t_start_orig

            if t_start < t_end:
                vwap_args = (pair, t_start, t_end)

        except Exception:
            curr_file = None
            vwap_args = (pair, t_start_orig, t_end)

        # Save if any new data
        if vwap_args is not None:
            print(f"Downloading {pair[0]}-{pair[1]}")
            data = vwap_agg_sync(*vwap_args)
            if curr_file is not None:
                data = pd.concat([curr_file, data])
            data = data[data.index >= t_start_orig]
            os.makedirs(data_dir, exist_ok=True)
            data.to_csv(f_name)


def pool_prices(  # noqa: C901
    coins=[],
    quote=None,
    quotediv=False,
    t_start=None,
    t_end=None,
    resample=None,
    pairs=[],
    data_dir="data",
):
    """
    Loads and formats price/volume data from CSVs.

    Parameters
    ----------
    coins: list of str
        List of coin addresses to load. Data loaded for pairwise combinations.

    quote: str, optional
        Name of an additional quote currency to use.

    quotediv: bool
        Determine pairwise coin prices using third currency
        (e.g., ETH-SUSD/SETH-SUSD for ETH-SETH).

    t_start/t_end:
        Used to truncate input time series.

    resample:
        Used to downsample input time series.

    pairs: list
        List of coin addresses to load. Data loaded for each listed pair.

    data_dir: str
        Base directory name for price csv files.

    Returns
    -------
    prices : pandas.DataFrame
        Timestamped prices for each pair of coins.

    volumes : pandas.DataFrame
        Timestamped volumes for each pair of coins.

    pzero : pandas.Series
        Proportion of timestamps with zero volume.
    """
    loop = asyncio.get_event_loop()

    if pairs and coins:
        raise ValueError("Use only 'coins' or 'pairs', not both.")

    if coins:
        coins = coin_ids_from_addresses_sync(coins, event_loop=loop)

        if quote:
            quote = coin_ids_from_addresses_sync(quote, event_loop=loop)
            symbol_pairs = zip(coins, [quote] * len(coins))

        else:
            symbol_pairs = list(combinations(coins, 2))

    elif pairs:
        pairs = coin_ids_from_addresses_sync(pairs, event_loop=loop)
        symbol_pairs = pairs

    else:
        raise ValueError("Must use one of 'coins' or 'pairs'.")

    prices = []
    volumes = []
    for (sym_1, sym_2) in symbol_pairs:
        filename = os.path.join(data_dir, f"{sym_1}-{sym_2}.csv")
        data_df = pd.read_csv(filename, index_col=0)
        prices.append(data_df["price"])
        volumes.append(data_df["volume"])

    prices = pd.concat(prices, axis=1)
    volumes = pd.concat(volumes, axis=1)

    pzero = (volumes == 0).mean()

    prices = prices.replace(
        to_replace=0, method="ffill"
    )  # replace price=0 with previous price
    prices = prices.replace(
        to_replace=0, method="bfill"
    )  # replace any price=0 at beginning with subsequent price

    # If quotediv, calc prices for each coin pair from prices in quote currency
    if quotediv:
        combos = list(combinations(range(len(coins)), 2))
        prices_tmp = []
        volumes_tmp = []

        for pair in combos:
            prices_tmp.append(
                prices.iloc[:, pair[0]] / prices.iloc[:, pair[1]]
            )  # divide prices
            volumes_tmp.append(
                volumes.iloc[:, pair[0]] + volumes.iloc[:, pair[1]]
            )  # sum volumes

        prices = pd.concat(prices_tmp, axis=1)
        volumes = pd.concat(volumes_tmp, axis=1)

    # Index as date-time type
    prices.index = pd.to_datetime(prices.index)
    volumes.index = pd.to_datetime(volumes.index)

    # Trim to t_start and/or t_end
    if t_start is not None:
        prices = prices.loc[t_start:]
        volumes = volumes.loc[t_start:]

    if t_end is not None:
        prices = prices.loc[:t_end]
        volumes = prices.loc[:t_end]

    # Resample times
    if resample is not None:
        prices = prices.resample(resample).first()
        volumes = volumes.resample(resample).sum()
    else:
        prices.index.freq = pd.infer_freq(prices.index)
        volumes.index.freq = pd.infer_freq(volumes.index)

    return prices, volumes, pzero


def local_pool_prices(  # noqa: C901
    coins=[],
    quote=None,
    quotediv=False,
    t_start=None,
    t_end=None,
    resample=None,
    pairs=[],
    data_dir="data",
):
    """
    Loads and formats price/volume data from CSVs.

    Parameters
    ----------
    coins: list of str
        List of coin names/addresses to load. Data loaded for pairwise combinations.

    quote: str, optional
        Name of an additional quote currency to use.

    quotediv: bool
        Determine pairwise coin prices using third currency
        (e.g., ETH-SUSD/SETH-SUSD for ETH-SETH).

    t_start/t_end:
        Used to truncate input time series.

    resample:
        Used to downsample input time series.

    pairs: list
        List of coin names/addresses to load. Data loaded for each listed pair.

    data_dir: str
        Base directory name for price csv files.

    Returns
    -------
    prices : pandas.DataFrame
        Timestamped prices for each pair of coins.

    volumes : pandas.DataFrame
        Timestamped volumes for each pair of coins.

    pzero : pandas.Series
        Proportion of timestamps with zero volume.
    """

    if pairs and coins:
        raise ValueError("Use only 'coins' or 'pairs', not both.")

    if coins:
        if quote:
            symbol_pairs = zip(coins, [quote] * len(coins))
        else:
            symbol_pairs = list(combinations(coins, 2))
    elif pairs:
        symbol_pairs = pairs
    else:
        raise ValueError("Must use one of 'coins' or 'pairs'.")

    prices = []
    volumes = []
    for (sym_1, sym_2) in symbol_pairs:
        filename = os.path.join(data_dir, f"{sym_1}-{sym_2}.csv")
        data_df = pd.read_csv(filename, index_col=0)
        prices.append(data_df["price"])
        volumes.append(data_df["volume"])

    prices = pd.concat(prices, axis=1)
    volumes = pd.concat(volumes, axis=1)

    pzero = (prices == 0).mean()

    prices = prices.replace(
        to_replace=0, method="ffill"
    )  # replace price=0 with previous price
    prices = prices.replace(
        to_replace=0, method="bfill"
    )  # replace any price=0 at beginning with subsequent price

    # If quotediv, calc prices for each coin pair from prices in quote currency
    if quotediv:
        combos = list(combinations(range(len(coins)), 2))
        prices_tmp = []
        volumes_tmp = []

        for pair in combos:
            prices_tmp.append(
                prices.iloc[:, pair[0]] / prices.iloc[:, pair[1]]
            )  # divide prices
            volumes_tmp.append(
                volumes.iloc[:, pair[0]] + volumes.iloc[:, pair[1]]
            )  # sum volumes

        prices = pd.concat(prices_tmp, axis=1)
        volumes = pd.concat(volumes_tmp, axis=1)

    # Index as date-time type
    prices.index = pd.to_datetime(prices.index)
    volumes.index = pd.to_datetime(volumes.index)

    # Trim to t_start and/or t_end
    if t_start is not None:
        prices = prices.loc[t_start:]
        volumes = volumes.loc[t_start:]

    if t_end is not None:
        prices = prices.loc[:t_end]
        volumes = prices.loc[:t_end]

    # Resample times
    if resample is not None:
        prices = prices.resample(resample).first()
        volumes = volumes.resample(resample).sum()
    else:
        prices.index.freq = pd.infer_freq(prices.index)
        volumes.index.freq = pd.infer_freq(volumes.index)

    return prices, volumes, pzero


async def _coin_id_from_address(address):
    if address == ETH_addr:
        return "ETH"

    url = URL + "currencies"
    address = address.lower()
    p = {"key": key, "platform-contract": address}

    r = await HTTP.get(url, params=p)

    coin_id = r[0]["id"]

    return coin_id


async def coin_ids_from_addresses(addresses):
    if isinstance(addresses, str):
        coin_ids = await _coin_id_from_address(addresses)

    else:
        tasks = []
        for addr in addresses:
            tasks.append(_coin_id_from_address(addr))

        coin_ids = await asyncio.gather(*tasks)

    return coin_ids


# Sync
get_data_sync = sync(get_data)
get_mkt_sync = sync(get_mkt)
get_agg_sync = sync(get_agg)
vwap_mkt_sync = sync(vwap_mkt)
vwap_agg_sync = sync(vwap_agg)
coin_ids_from_addresses_sync = sync(coin_ids_from_addresses)
