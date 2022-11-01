from asyncio import gather
from datetime import datetime, timedelta, timezone

import pandas as pd
from eth_utils import to_checksum_address

from .http import HTTP
from .utils import compute_D, sync


async def query(url, q):
    r = await HTTP.post(url, json={"query": q})
    return r


query_sync = sync(query)


# Convex Community subgraphs
CONVEX_COMMUNITY_URL = (
    "https://api.thegraph.com/subgraphs/name/convex-community/volume-%s"
)


async def convex(chain, q):
    url = CONVEX_COMMUNITY_URL % chain
    r = await query(url, q)
    return r


async def symbol_address(symbol, chain):
    q = (
        """
        {
          pools(
            where:
              {symbol_starts_with_nocase: "%s"}
          )
          {
            address
          }
        }
    """
        % symbol
    )

    r = await convex(chain, q)
    addr = to_checksum_address(r["data"]["pools"][0]["address"])

    return addr


async def _volume(address, chain, days=60):
    t_end = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
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
                timestamp_lte: %d
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

    r = await convex(chain, q)
    r = r["data"]["swapVolumeSnapshots"]
    r_length = len(r)

    if r_length < days:
        print(f"Warning: only {r_length}/{days} days of pool volume returned")

    return r


async def volume(addresses, chain, days=60):
    if isinstance(addresses, str):
        r = await _volume(addresses, chain, days=days)
        vol = [float(e["volume"]) for e in r]

    else:
        tasks = []
        for addr in addresses:
            tasks.append(_volume(addr, chain, days=days))

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
              poolType
              isV2
            }

            A
            fee
            offPegFeeMultiplier
            normalizedReserves
            virtualPrice
            timestamp
          }
        }
    """
        % address.lower()
    )

    r = await convex(chain, q)
    r = r["data"]["dailyPoolSnapshots"][0]

    return r


async def pool_snapshot(address, chain):
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
    addrs = [to_checksum_address(c) for c in r["coins"]]

    coins = {"names": r["coinNames"], "addresses": addrs}

    # Reserves
    reserves = [int(nr) for nr in r["normalizedReserves"]]

    # Basepool
    if r["metapool"]:
        basepool = await pool_snapshot(r["basePool"], chain)
    else:
        basepool = None

    # Output
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
        },
        "coins": coins,
        "reserves": {
            "D": D,
            "by_coin": reserves,
            "virtual_price": int(r["virtualPrice"]),
            "tokens": D * 10**18 // int(r["virtualPrice"]),
        },
        "basepool": basepool,
        "timestamp": int(r["timestamp"]),
    }

    # Kwargs for Pool Init
    init_kwargs = {
        "A": data["params"]["A"],
        "D": D,
        "reserves": reserves,
        "n": len(data["coins"]["names"]),
        "fee": data["params"]["fee"],
        "fee_mul": data["params"]["fee_mul"],
        "tokens": data["reserves"]["tokens"],
    }

    data.update({"init_kwargs": init_kwargs})

    return data


convex_sync = sync(convex)
symbol_address_sync = sync(symbol_address)
volume_sync = sync(volume)
pool_snapshot_sync = sync(pool_snapshot)


# Reflexer Subgraph
RAI_ADDR = ("0x618788357D0EBd8A37e763ADab3bc575D54c2C7d", "mainnet")


async def _redemption_prices(address, chain, t_start, t_end, n):
    if (address, chain) != RAI_ADDR:
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


async def redemption_prices(address=RAI_ADDR[0], chain=RAI_ADDR[1], days=60, n=1000):

    t_end = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
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
