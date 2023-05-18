"""
Network connector for subgraphs
"""

from asyncio import gather
from datetime import datetime, timedelta, timezone

import pandas as pd
from eth_utils import to_checksum_address

from curvesim.logging import get_logger

from ..exceptions import SubgraphResultError
from ..overrides import override_subgraph_data
from .http import HTTP
from .utils import compute_D, sync

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


async def convex(chain, q):
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
    url = CONVEX_COMMUNITY_URL % chain
    r = await query(url, q)
    if "data" not in r:
        raise SubgraphResultError(
            f"No data returned from Convex: chain: {chain}, query: {q}"
        )
    return r["data"]


async def symbol_address(symbol, chain):
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
    q = (
        """
        {
          pools(
            where:
              {symbol_starts_with_nocase: "%s"}
          )
          {
            symbol
            address
          }
        }
    """
        % symbol
    )

    data = await convex(chain, q)

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


async def _volume(address, chain, days=60, end=None):
    if end is None:
        t_end = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    else:
        t_end = datetime.fromtimestamp(end, tz=timezone.utc)
    logger.info(f"Volume end date: {t_end}")
    t_start = t_end - timedelta(days=days)

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

    data = await convex(chain, q)
    snapshots = data["swapVolumeSnapshots"]
    num_snapshots = len(snapshots)

    if num_snapshots < days:
        logger.warning(f"Only {num_snapshots}/{days} days of pool volume returned.")

    return snapshots


async def volume(addresses, chain, days=60, end=None):
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
        r = await _volume(addresses, chain, days=days, end=end)
        vol = [float(e["volume"]) for e in r]

    else:
        tasks = []
        for addr in addresses:
            tasks.append(_volume(addr, chain, days=days, end=end))

        r = await gather(*tasks)

        vol = []
        for _r in r:
            _vol = [float(e["volume"]) for e in _r]
            vol.append(_vol)

    return vol


async def _pool_snapshot(address, chain):
    q = (
        """
        {
          dailyPoolSnapshots(
            orderBy: timestamp,
            orderDirection: desc,
            first: 1,
            where:
              {
                pool: "%s"
              }
          )
          {
            pool {
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
            }

            A
            fee
            adminFee
            offPegFeeMultiplier
            reserves
            normalizedReserves
            virtualPrice
            timestamp

            gamma
            midFee
            outFee
            feeGamma
            allowedExtraProfit
            adjustmentStep
            maHalfTime
            priceScale
            priceOracle
            lastPrices
            lastPricesTimestamp
            xcpProfit
            xcpProfitA
          }
        }
    """
        % address.lower()
    )

    r = await convex(chain, q)
    try:
        r = r["dailyPoolSnapshots"][0]
    except IndexError:
        raise SubgraphResultError(
            f"No daily snapshot for this pool: {address}, {chain}"
        )

    return r


async def pool_snapshot(address, chain):
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
    r = await _pool_snapshot(address, chain)

    # Flatten
    pool = r.pop("pool")
    r.update(pool)

    # D
    D = compute_D(r["normalizedReserves"], r["A"])

    # Version
    if r["isV2"]:
        version = 2
    else:
        version = 1

    # Fee_mul
    if r["offPegFeeMultiplier"] == "0":
        fee_mul = None
    else:
        fee_mul = int(r["offPegFeeMultiplier"]) * 10**10

    # Coins
    names = r["coinNames"]
    addrs = [to_checksum_address(c) for c in r["coins"]]
    decimals = [int(d) for d in r["coinDecimals"]]

    coins = {"names": names, "addresses": addrs, "decimals": decimals}

    # Reserves
    normalized_reserves = [int(r) for r in r["normalizedReserves"]]
    unnormalized_reserves = [int(r) for r in r["reserves"]]

    # Basepool
    if r["metapool"]:
        basepool = await pool_snapshot(r["basePool"], chain)
    else:
        basepool = None

    # Output
    if version == 1:
        data = {
            "name": r["name"],
            "address": to_checksum_address(r["address"]),
            "chain": chain,
            "symbol": r["symbol"].strip(),
            "version": version,
            "pool_type": r["poolType"],
            "params": {
                "A": int(r["A"]),
                "fee": int(float(r["fee"]) * 10**10),
                "fee_mul": fee_mul,
                "admin_fee": int(r["adminFee"]),
            },
            "coins": coins,
            "reserves": {
                "D": D,
                "by_coin": normalized_reserves,
                "unnormalized_by_coin": unnormalized_reserves,
                "virtual_price": int(r["virtualPrice"]),
                "tokens": D * 10**18 // int(r["virtualPrice"]),
            },
            "basepool": basepool,
            "timestamp": int(r["timestamp"]),
        }
    else:
        data = {
            "name": r["name"],
            "address": to_checksum_address(r["address"]),
            "chain": chain,
            "symbol": r["symbol"].strip(),
            "version": version,
            "pool_type": r["poolType"],
            "params": {
                "A": int(r["A"]),
                "gamma": int(r["gamma"]),
                "fee_gamma": int(r["feeGamma"]),
                "mid_fee": int(r["midFee"]),
                "out_fee": int(r["outFee"]),
                "allowed_extra_profit": int(r["allowedExtraProfit"]),
                "adjustment_step": int(r["adjustmentStep"]),
                "ma_half_time": int(r["adjustmentStep"]),
                "price_scale": int(r["priceScale"]),
                "price_oracle": int(r["priceOracle"]),
                "last_prices": int(r["lastPrices"]),
                "last_prices_timestamp": int(r["lastPricesTimestamp"]),
                "admin_fee": int(r["adminFee"]),
                "xcp_profit": int(r["xcpProfit"]),
                "xcp_profit_a": int(r["xcpProfitA"]),
            },
            "coins": coins,
            "reserves": {
                "D": D,
                "by_coin": normalized_reserves,
                "unnormalized_by_coin": unnormalized_reserves,
                "virtual_price": int(r["virtualPrice"]),
                "tokens": D * 10**18 // int(r["virtualPrice"]),
            },
            "basepool": basepool,
            "timestamp": int(r["timestamp"]),
        }

    return override_subgraph_data(data, "pool_snapshot", (address, chain))


convex_sync = sync(convex)
symbol_address_sync = sync(symbol_address)
volume_sync = sync(volume)
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
