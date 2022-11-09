"""
Network connector for Coingecko.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from itertools import combinations

import numpy as np
import pandas as pd

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


async def _get_prices(coin_id, vs_currency, days):
    url = URL + f"coins/{coin_id}/market_chart"
    p = {"vs_currency": vs_currency, "days": days}

    r = await HTTP.get(url, params=p)

    return r


async def get_prices(coin_id, vs_currency, days):
    r = await _get_prices(coin_id, vs_currency, days)

    # Format data
    data = pd.DataFrame(r["prices"], columns=["timestamp", "prices"])
    data = data.merge(
        pd.DataFrame(r["total_volumes"], columns=["timestamp", "volumes"])
    )
    data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms", utc="True")
    data = data.set_index("timestamp")

    return data


async def _pool_prices(coins, vs_currency, days):
    # Times to reindex to: hourly intervals starting on half hour mark
    t_end = datetime.utcnow() - timedelta(days=1)
    t_end = t_end.replace(hour=23, minute=30, second=0, microsecond=0)
    t_start = t_end - timedelta(days=days + 1)
    t_samples = pd.date_range(start=t_start, end=t_end, freq="60T", tz=timezone.utc)

    # Fetch data
    tasks = []
    for coin in coins:
        tasks.append(get_prices(coin, vs_currency, days + 3))

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


def pool_prices(coins, vs_currency, days):
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
    coins = coin_ids_from_addresses_sync(coins, "mainnet")
    qprices, qvolumes = _pool_prices_sync(coins, vs_currency, days)

    # Compute prices by coin pairs
    combos = list(combinations(range(len(coins)), 2))
    prices = []
    volumes = []

    for pair in combos:
        prices.append(
            qprices.iloc[:, pair[0]] / qprices.iloc[:, pair[1]]
        )  # divide prices
        volumes.append(
            qvolumes.iloc[:, pair[0]] + qvolumes.iloc[:, pair[1]]
        )  # sum volumes

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


async def _coin_info_from_id(ID, chain, chain_out="mainnet"):
    chain = PLATFORMS[chain.lower()]
    chain_out = PLATFORMS[chain_out.lower()]
    url = URL + f"coins/{ID}"

    r = await HTTP.get(url)
    address = r["platforms"][chain_out]
    symbol = r["symbol"]

    return address, symbol


async def coin_info_from_ids(IDs, chain, chain_out="mainnet"):
    if isinstance(IDs, str):
        addresses, symbols = await _coin_info_from_id(IDs, chain, chain_out=chain_out)

    else:
        tasks = []
        for ID in IDs:
            tasks.append(_coin_info_from_id(ID, chain, chain_out=chain_out))

        r = await asyncio.gather(*tasks)
        addresses, symbols = list(zip(*r))

    return addresses, symbols


async def _crosschain_coin_address(address, chain_in, chain_out):
    if chain_in == "mainnet" and chain_out == "mainnet":
        return address

    address = address.lower()
    chain_in = PLATFORMS[chain_in.lower()]
    chain_out = PLATFORMS[chain_out.lower()]
    url = URL + f"coins/{chain_in}/contract/{address}"

    r = await HTTP.get(url)

    address = r["platforms"][chain_out]

    return address


async def crosschain_coin_addresses(addresses, chain_in, chain_out):
    if isinstance(addresses, str):
        addresses_out = await _crosschain_coin_address(addresses, chain_in, chain_out)

    else:
        tasks = []
        for addr in addresses:
            tasks.append(_crosschain_coin_address(addr, chain_in, chain_out))

        addresses_out = await asyncio.gather(*tasks)

    return addresses_out


# Sync
_pool_prices_sync = sync(_pool_prices)
coin_ids_from_addresses_sync = sync(coin_ids_from_addresses)
coin_info_from_ids_sync = sync(coin_info_from_ids)
crosschain_coin_addresses_sync = sync(crosschain_coin_addresses)


if __name__ == "__main__":
    coin_addresses = [
        "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    ]
    chain = "mainnet"
    print("Coin addresses:", coin_addresses)
    print("Chain", chain)
    coin_ids = coin_ids_from_addresses_sync(coin_addresses, chain)
    print("Coin IDs:", coin_ids)

    vs_ccy = "USD"
    days = 1
    prices, volumes = pool_prices(coin_addresses, vs_ccy, days)
    print(prices.head())
    print(volumes.head())
