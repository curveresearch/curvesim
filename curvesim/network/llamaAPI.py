"""
Network connector for LLama Airforce REST API.
"""
from asyncio import gather

from eth_utils import to_checksum_address
from numpy import array

from .http import HTTP
from .utils import sync

URL = "https://api-py.llama.airforce/curve/v1/"


# Query Llama Airforce API
async def llamaAPI(endpoint):
    path = "/"
    path = path.join(endpoint)
    url = URL + path

    r = await HTTP.get(url)

    return r


# Specific Queries
async def pools(chain):
    r = await llamaAPI(["pools", chain, "all"])
    pools = r["pools"]

    return pools


async def pool_metadata(address, chain):
    address = address.lower()
    r = await llamaAPI(["pools", chain, address])
    pool = r["pools"][0]

    return pool


async def symbol_address(symbol, chain):
    pls = await pools(chain)

    for pool in pls:
        if pool["symbol"] == symbol:
            addr = to_checksum_address(pool["address"])
            return addr

    raise ValueError("Address for pool symbol not found")


async def volume(address, chain, bp=None, days=60, inUSD=True):
    address = address.lower()

    key = "volume"
    if inUSD:
        key = key + "USD"

    if bp is None:
        r = await llamaAPI(["pools", chain, "volume", address])

        sum_volume = array(0.0)
        for i in range(days):
            sum_volume += r["volume"][i][key]

    else:
        tasks = [
            llamaAPI(["pools", chain, "volume", address]),
            llamaAPI(["pools", chain, "volume", bp]),
        ]

        r_meta, r_base = await gather(*tasks)

        sum_volume = array([0.0, 0.0])
        for i in range(days):
            sum_volume += [r_meta["volume"][i][key], r_base["volume"][i][key]]

    return sum_volume


async def reserves(address, chain):
    address = address.lower()
    r = await llamaAPI(["pools", chain, "reserves", address])
    reserves = r["reserves"]

    return reserves


async def latest_reserves(address, chain, p=10**18, bp=None, inUSD=True):

    key = "reserves"
    if inUSD:
        key = key + "USD"

    if bp is None:
        res = await reserves(address, chain)
        curr_reserves = res[0][key]
        curr_reserves = [int(r * p) for r in curr_reserves]

    else:
        curr_reserves = await gather(
            latest_reserves(address, chain, p=p, inUSD=inUSD),
            latest_reserves(bp, chain, p=p, inUSD=inUSD),
        )

    return curr_reserves


# Sync
llamaAPI_sync = sync(llamaAPI)
pools_sync = sync(pools)
pool_metadata_sync = sync(pool_metadata)
symbol_address_sync = sync(symbol_address)
volume_sync = sync(volume)
reserves_sync = sync(reserves)
latest_reserves_sync = sync(latest_reserves)
