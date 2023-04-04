"""
Network connector for subgraphs
"""

from asyncio import gather
from datetime import datetime, timedelta, timezone

import pandas as pd

from curvesim.exceptions import SubgraphResultError
from curvesim.network.http import AsyncHttpClient
from curvesim.network.subgraph.pool_snapshot import (
    pool_snapshot_query,
    process_pool_snapshot_result,
)
from curvesim.network.utils import sync

from .symbol_address import process_symbol_address_result, symbol_address_query
from .volume import process_volume_result, volume_query

# pylint: disable=redefined-outer-name

CONVEX_COMMUNITY_URL = (
    "https://api.thegraph.com/subgraphs/name/convex-community/volume-%s"
)


class ConvexSubgraphClient(AsyncHttpClient):
    """
    Async function to query convex community subgraphs

    Parameters
    ----------
    chain : str
        The chain of interest.

        Currently supports:
        ”mainnet”, “arbitrum”, “optimism”, “fantom”, “avalanche” “matic”, “xdai”

    q : str
        A GraphQL query.

    Returns
    -------
    str
        The returned results.

    """

    def __init__(self, chain):
        self.url = CONVEX_COMMUNITY_URL % chain

    async def query(self, q):
        r = await self.post(self.url, json={"query": q})
        if "data" not in r:
            raise SubgraphResultError(
                f"No data returned from Convex: chain: {chain}, query: {q}"
            )
        return r["data"]

    query_sync = sync(query)

    async def multiple_queries(self, queries):
        tasks = [self.query(q) for q in queries]
        results = await gather(tasks)
        return results

    async def symbol_address(self, symbol):
        """
        Async function to get a pool's address from it's (LP token) symbol.

        Parameters
        ----------
        symbol: str
            The pool's (LP token) symbol

        .. warning::
            An LP token symbol need not be unique.  In particular, factory pools
            are deployed permissionlessly and no checks are done to ensure unique
            LP token symbol.  Currently the first pool retrieved from the subgraph
            is used, which can be effectively random if token symbols clash.

        chain : str
            The pool's chain.

            Currently supports:
            ”mainnet”, “arbitrum”, “optimism”, “fantom”, “avalanche” “matic”, “xdai”


        Returns
        -------
        str
            Pool address.

        """
        q = symbol_address_query(symbol)
        data = await self.query(q)
        address = process_symbol_address_result(data)
        return address

    symbol_address_sync = sync(symbol_address)

    async def volume(self, addresses, days=60, end=None):
        """
        Retrieves historical volume for a pool or multiple pools.

        Parameters
        ----------
        addresses : str or iterable of str
            The pool address(es).

        chain : str
            The blockchain the pool or pools are on.

        days : int, default=60
            Number of days to fetch data for.

        Returns
        -------
        list of float
            A list of total volumes for each day.

        """
        queries = volume_query(addresses, days, end)
        results = await self.multiple_queries(queries)
        volumes = process_volume_result(results, days)
        return volumes

    volume_sync = sync(volume)

    async def pool_snapshot(self, address):
        """
        Async function to pull pool state and metadata from daily snapshots.

        Parameters
        ----------
        address : str
            The pool address.

        chain : str
            The blockchain the pool is on.

        Returns
        -------
        dict
            A formatted dict of pool state/metadata information.

        """
        q = pool_snapshot_query(address)
        result = await self.query(q)
        snapshot = process_pool_snapshot_result(result)
        return snapshot

    pool_snapshot_sync = sync(pool_snapshot)


# Reflexer Subgraph
RAI_ADDR = ("0x618788357D0EBd8A37e763ADab3bc575D54c2C7d", "mainnet")


def has_redemption_prices(address, chain):
    return (address, chain) == RAI_ADDR


async def _redemption_prices(address, chain, t_start, t_end, n):
    if not has_redemption_prices(address, chain):
        return None

    t_end = int(t_end.timestamp())
    t_start = int(t_start.timestamp())

    url = "https://api.thegraph.com/subgraphs/name/reflexer-labs/rai-mainnet"
    q = """{
        redemptionPrices(
            orderBy: timestamp,
            orderDirection: desc,
            first: %d,
            where: {timestamp_lte: %d}
        )
        {
            timestamp
            value
        }
    }"""

    t_earliest = t_end
    data = []
    while t_earliest >= t_start:
        r = await query(url, q % (n, t_earliest))
        data += r["data"]["redemptionPrices"]
        t_earliest = int(data[-1]["timestamp"])
    return data


async def redemption_prices(
    address=RAI_ADDR[0], chain=RAI_ADDR[1], days=60, n=1000, end=None
):
    """
    Async function to pull RAI redemption prices.
    Returns None if input pool is not RAI3CRV.

    Parameters
    ----------
    address : str
        The pool address.

    chain : str
        The blockchain the pool is on.

    days : int, default=60
        Number of days to fetch data for.

    n : int, default=1000
        Number of data entries to request per query (max: 1000)

        Note: the function will re-query until the requested time range is complete.


    Returns
    -------
    dict
        A formatted dict of pool state/metadata information.

    """
    if end is None:
        t_end = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        t_end = datetime.fromtimestamp(end, tz=timezone.utc)
    t_end = t_end.replace(tzinfo=timezone.utc)
    t_start = t_end - timedelta(days=days)

    r = await _redemption_prices(address, chain, t_start, t_end, n)

    if r is None:
        return None

    data = pd.DataFrame(r)
    data.columns = ["timestamp", "price"]
    data.price = (data.price.astype(float) * 10**18).astype(int)
    data.timestamp = pd.to_datetime(data.timestamp, unit="s", utc=True)
    data.sort_values("timestamp", inplace=True)
    data.set_index("timestamp", inplace=True)
    data.drop_duplicates(inplace=True)

    t0 = data.index.asof(t_start)

    return data[data.index >= t0]


redemption_prices_sync = sync(redemption_prices)

if __name__ == "__main__":
    chain = "mainnet"
    symbol = "3Crv"
    print("Chain:", chain)
    print("Symbol:", symbol)
    address = symbol_address_sync(symbol, chain)
    print("Address:", address)
    _volume_sync = sync(_volume)
    volumes = _volume_sync(address, chain, days=2)
    print("Volumes:", volumes)
