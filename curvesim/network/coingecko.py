"""
Network connector for Coingecko.
"""
# pylint: disable=redefined-outer-name
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


async def _get_prices(coin_id, vs_currency, start, end):
    url = URL + f"coins/{coin_id}/market_chart/range"
    p = {"vs_currency": vs_currency, "from": start, "to": end}

    r = await HTTP.get(url, params=p)

    return r


async def get_prices(coin_id, vs_currency, start, end):
    r = await _get_prices(coin_id, vs_currency, start, end)

    # Format data
    data = pd.DataFrame(r["prices"], columns=["timestamp", "price"])
    data = data.merge(pd.DataFrame(r["total_volumes"], columns=["timestamp", "volume"]))
    data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms", utc="True")
    data = data.set_index("timestamp")

    return data


async def coin_id_from_address(address, chain):
    address = address.lower()
    chain = PLATFORMS[chain.lower()]
    url = URL + f"coins/{chain}/contract/{address}"

    r = await HTTP.get(url)

    coin_id = r["id"]

    return coin_id


# Sync
get_prices_sync = sync(get_prices)
coin_id_from_address_sync = sync(coin_id_from_address)


if __name__ == "__main__":
    coin_addresses = [
        "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    ]
    chain = "mainnet"
    vs_ccy = "USD"
    end = 1708403238
    start = end - 68400

    for address in coin_addresses:
        coin_id = coin_id_from_address_sync(address, chain)
        data = get_prices_sync(coin_id, vs_ccy, start, end)
        print(f"\n{coin_id.upper()}: {address} ({chain})")
        print(data.head())
