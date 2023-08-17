"""
Network connector for Coingecko.
"""
# pylint: disable=redefined-outer-name
import asyncio
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from curvesim.utils import get_pairs

from .http import HTTP
from .utils import sync

URL = "https://api.coingecko.com/api/v3/"

PLATFORMS = {
    "mainnet": "ethereum",
    "arbitrum": "arbitrum-one",
    "polygon": "polygon-pos",
    "optimism": "optimistic-ethereum",
    "xdai": "xdai",
    "fantom": "fantom",
    "avalanche": "avalanche",
    "matic:": "polygon-pos",
}


async def _get_prices(coin_id, vs_currency, start, end):
    url = URL + f"coins/{coin_id}/market_chart/range"
    p = {"vs_currency": vs_currency, "from": start, "to": end}

    r = await HTTP.get(url, params=p)

    return r


async def get_prices(coin_id, vs_currency, start, end):
    r = await _get_prices(coin_id, vs_currency, start, end)

    # Format data
    data = pd.DataFrame(r["prices"], columns=["timestamp", "prices"])
    data = data.merge(
        pd.DataFrame(r["total_volumes"], columns=["timestamp", "volumes"])
    )
    data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms", utc="True")
    data = data.set_index("timestamp")

    return data


async def _pool_prices(coins, vs_currency, days, end=None):
    if end is not None:
        # Times to reindex to: daily intervals
        # Coingecko only allows daily data when more than 90 days in the past
        # for the free REST endpoint
        t_end = datetime.fromtimestamp(end, tz=timezone.utc)
        t_start = t_end - timedelta(days=days + 1)
        t_samples = pd.date_range(start=t_start, end=t_end, freq="1D", tz=timezone.utc)
    else:
        # Times to reindex to: hourly intervals starting on half hour mark
        t_end = datetime.now(timezone.utc) - timedelta(days=1)
        t_end = t_end.replace(hour=23, minute=30, second=0, microsecond=0)
        t_start = t_end - timedelta(days=days + 1)
        t_samples = pd.date_range(start=t_start, end=t_end, freq="60T", tz=timezone.utc)
        end = t_end.timestamp()

    # Fetch data
    tasks = []
    for coin in coins:
        start = t_start.timestamp() - 86400 * 3
        tasks.append(get_prices(coin, vs_currency, start, end))

    data = await asyncio.gather(*tasks)

    # Format data
    qprices = []
    qvolumes = []
    for d in data:
        d.drop(d.tail(1).index, inplace=True)  # remove last row
        d = d.reindex(t_samples, method="ffill")
        qprices.append(d["prices"])
        qvolumes.append(d["volumes"])

    qprices = pd.concat(qprices, axis=1)
    qvolumes = pd.concat(qvolumes, axis=1)
    qvolumes = qvolumes / np.array(qprices)

    return qprices, qvolumes


def pool_prices(coins, vs_currency, days, chain="mainnet", end=None):
    """
    Pull price and volume data for given coins, quoted in given
    quote currency for given days.

    Parameters
    ----------
    coins: list of str
        List of coin addresses.
    vs_currency: str
        Symbol for quote currency.
    days: int
        Number of days to pull data for.

    Returns
    -------
    pair of pandas.Series
        prices Series and volumes Series
    """
    # Get data
    coins = coin_ids_from_addresses_sync(coins, chain)
    qprices, qvolumes = _pool_prices_sync(coins, vs_currency, days, end)

    # Compute prices by coin pairs
    combos = get_pairs(len(coins))
    prices = []
    volumes = []

    for pair in combos:
        base_price = qprices.iloc[:, pair[0]]
        base_volume = qvolumes.iloc[:, pair[0]]

        quote_price = qprices.iloc[:, pair[1]]
        quote_volume = qvolumes.iloc[:, pair[1]]

        # divide prices: (usd/base) / (usd/quote) = quote/base
        prices.append(base_price / quote_price)
        # sum volumes and convert to base: usd / (usd/base) = base
        volumes.append((base_volume + quote_volume) / base_price)

    prices = pd.concat(prices, axis=1)
    volumes = pd.concat(volumes, axis=1)

    return prices, volumes


async def _coin_id_from_address(address, chain):
    address = address.lower()
    chain = PLATFORMS[chain.lower()]
    url = URL + f"coins/{chain}/contract/{address}"

    r = await HTTP.get(url)

    coin_id = r["id"]

    return coin_id


async def coin_ids_from_addresses(addresses, chain):
    if isinstance(addresses, str):
        coin_ids = await _coin_id_from_address(addresses, chain)

    else:
        tasks = []
        for addr in addresses:
            tasks.append(_coin_id_from_address(addr, chain))

        coin_ids = await asyncio.gather(*tasks)

    return coin_ids


# Sync
_pool_prices_sync = sync(_pool_prices)
coin_ids_from_addresses_sync = sync(coin_ids_from_addresses)


if __name__ == "__main__":
    coin_addresses = [
        "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    ]
    chain = "mainnet"
    print("Coin addresses:", coin_addresses)
    print("Chain", chain)

    vs_ccy = "USD"
    days = 1
    prices, volumes = pool_prices(coin_addresses, vs_ccy, days, chain)
    print(prices.head())
    print(volumes.head())
