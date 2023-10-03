"""
Network connector for subgraphs
"""

from asyncio import gather
from datetime import datetime, timedelta, timezone

import pandas as pd
from eth_utils import to_checksum_address

from curvesim.logging import get_logger

from ..exceptions import CurvesimValueError, SubgraphResultError
from ..overrides import override_subgraph_data
from .http import HTTP
from .utils import sync

# pylint: disable=redefined-outer-name

logger = get_logger(__name__)


async def query(url, q):
    """
    Core async function to query subgraphs.

    Parameters
    ----------
    url : str
        URL for the subgraph.
    q : str
        A GraphQL query.

    Returns
    -------
    str
        The returned results.

    """
    r = await HTTP.post(url, json={"query": q})
    return r


query_sync = sync(query)


# Convex Community subgraphs
CONVEX_COMMUNITY_URL = (
    "https://api.thegraph.com/subgraphs/name/convex-community/volume-%s"
)
STAGING_CONVEX_COMMUNITY_URL = (
    "https://api.thegraph.com/subgraphs/name/convex-community/volume-%s-staging"
)

CHAIN_ALIASES = {"ethereum": "mainnet"}


def _get_subgraph_url(chain, env="prod"):
    if chain in CHAIN_ALIASES:
        chain = CHAIN_ALIASES[chain]

    if env.lower() == "prod":
        url = CONVEX_COMMUNITY_URL % chain
    elif env.lower() == "staging":
        url = STAGING_CONVEX_COMMUNITY_URL % chain
    else:
        raise CurvesimValueError("'env' must be 'prod' or 'staging'")

    return url


async def convex(chain, q, env):
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

    env: str
        Environment name.  Supported: "prod", "staging"

    Returns
    -------
    str
        The returned results.

    """
    url = _get_subgraph_url(chain, env)
    r = await query(url, q)
    if "data" not in r:
        raise SubgraphResultError(
            f"No data returned from Convex: chain: {chain}, query: {q}"
        )
    return r["data"]


async def symbol_address(symbol, chain, env="prod"):
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
    q = f"""
        {{
          pools(where: {{symbol_starts_with_nocase: "{symbol}"}})
          {{
            symbol
            address
          }}
        }}
    """

    data = await convex(chain, q, env)

    if len(data["pools"]) > 1:
        pool_list = "\n\n"
        for pool in data["pools"]:
            pool_list += f"\"{pool['symbol']}\": {pool['address']}\n"

        raise SubgraphResultError(
            "Multiple pools returned for symbol query:" + pool_list
        )
    if len(data["pools"]) < 1:
        raise SubgraphResultError("No pools found for symbol query.")

    addr = to_checksum_address(data["pools"][0]["address"])

    return addr


async def _volume(address, chain, env, days=60, end=None):
    if end is None:
        t_end = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    else:
        t_end = datetime.fromtimestamp(end, tz=timezone.utc)
    logger.info("Volume end date: %s", t_end)
    t_start = t_end - timedelta(days=days)

    # pylint: disable=consider-using-f-string
    q = """
        {
          swapVolumeSnapshots(
            orderBy: timestamp,
            orderDirection: desc,
            where:
              {
                pool: "%s"
                period: "86400"
                timestamp_gte: %d
                timestamp_lt: %d
              }
          )
          {
            volume
            timestamp
          }
        }
    """ % (
        address.lower(),
        int(t_start.timestamp()),
        int(t_end.timestamp()),
    )

    data = await convex(chain, q, env)
    snapshots = data["swapVolumeSnapshots"]
    num_snapshots = len(snapshots)

    if num_snapshots < days:
        logger.warning("Only %s/%s days of pool volume returned.", num_snapshots, days)

    return snapshots


async def volume(addresses, chain, env="prod", days=60, end=None):
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
    if isinstance(addresses, str):
        r = await _volume(addresses, chain, env, days=days, end=end)
        vol = [float(e["volume"]) for e in r]

    else:
        tasks = []
        for addr in addresses:
            tasks.append(_volume(addr, chain, env, days=days, end=end))

        r = await gather(*tasks)

        vol = []
        for _r in r:
            _vol = [float(e["volume"]) for e in _r]
            vol.append(_vol)

    return vol


async def _get_pool_info(address, chain, env="prod"):

    q = f"""
        {{
          pools(where: {{address: "{address.lower()}"}})
          {{
              name
              address
              symbol
              metapool
              basePool
              coins
              coinNames
              coinDecimals
              poolType
              isV2
          }}
        }}
    """

    r = await convex(chain, q, env)
    try:
        data = r["pools"][0]
    except IndexError as e:
        raise SubgraphResultError(
            f"No pool info returned for pool: {address}, {chain}"
        ) from e

    return override_subgraph_data(data, "_get_pool_info", (address, chain))


async def _get_pool_reserves(address, chain, end_ts=None, env="prod"):
    end_ts = end_ts or int(datetime.now(timezone.utc).timestamp())

    q = f"""
        {{
          dailyPoolSnapshots(
            orderBy: timestamp,
            orderDirection: desc,
            first: 1,
            where: {{pool: "{address.lower()}", timestamp_lte: {end_ts}}}
          )

          {{
            reserves
            normalizedReserves
            virtualPrice
            timestamp
          }}
        }}
    """
    r = await convex(chain, q, env)
    try:
        data = r["dailyPoolSnapshots"][0]
    except IndexError as e:
        raise SubgraphResultError(
            f"No pool reserves returned for pool: {address}, {chain}"
        ) from e

    return data


get_pool_info = sync(_get_pool_info)
get_pool_reserves = sync(_get_pool_reserves)

convex_sync = sync(convex)
symbol_address_sync = sync(symbol_address)
volume_sync = sync(volume)

# Reflexer Subgraph
RAI_ADDR = ("0x618788357D0EBd8A37e763ADab3bc575D54c2C7d", "mainnet")


def has_redemption_prices(address, chain):
    """
    Return True if the given pool has RAI redemption prices available.
    """
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
        t_end = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
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
