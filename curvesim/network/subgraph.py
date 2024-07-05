"""
Network connector for subgraphs
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pandas as pd
from eth_utils import to_checksum_address

from curvesim.logging import get_logger

from ..exceptions import CurvesimValueError, SubgraphResultError
from ..overrides import override_subgraph_data
from .http import HTTP
from .utils import sync

import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GRAPH_API_KEY')

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

# Subgraph URLs for different chains
MAINNET_URL = f"https://gateway-arbitrum.network.thegraph.com/api/{GRAPH_API_KEY}/subgraphs/id/6NkLKJQbjtpYir45Pvj61gvTkLeunEeEBFXGwisC35TB"
ARBITRUM_URL = f"https://gateway-arbitrum.network.thegraph.com/api/{GRAPH_API_KEY}/subgraphs/id/6okUrfq2HYokFytJd2JDhXW2kdyViy5gXWWpZkTnSL8w"
OPTIMISM_URL = f"https://gateway-arbitrum.network.thegraph.com/api/{GRAPH_API_KEY}/subgraphs/id/7cXBpS75ThtbYwtCD8B277vUfWptmz6vbhk9BKgYrEvQ"

# Convex Community subgraphs
# CONVEX_COMMUNITY_URL = "https://api.thegraph.com/subgraphs/name/convex-community/volume-%s"
# STAGING_CONVEX_COMMUNITY_URL = "https://api.thegraph.com/subgraphs/name/convex-community/volume-%s-staging"

def _get_subgraph_url(chain, env="prod"):    
    if env.lower() == "prod":
        if chain == "mainnet":
            url = MAINNET_URL
        elif chain == "arbitrum":
            url = ARBITRUM_URL
        elif chain == "optimism":
            url = OPTIMISM_URL
        else:
            url = ''   
    elif env.lower() == "staging":
        url = ''   
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

async def _pool_snapshot(address, chain, env, end_ts=None):
    if not end_ts:
        end_date = datetime.now(timezone.utc)
        end_ts = int(end_date.timestamp())

    q = """
        {
          dailyPoolSnapshots(
            orderBy: timestamp,
            orderDirection: desc,
            first: 1,
            where:
              {
                pool: "%s"
                timestamp_lte: %d
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
    """ % (
        address.lower(),
        end_ts,
    )

    r = await convex(chain, q, env)
    try:
        r = r["dailyPoolSnapshots"][0]
    except IndexError as e:
        raise SubgraphResultError(
            f"No daily snapshot for this pool: {address}, {chain}"
        ) from e

    return r

async def pool_snapshot(address, chain, env="prod", end_ts=None):
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
    r = await _pool_snapshot(address, chain, env, end_ts)
    logger.debug("Pool snapshot: %s", r)

    # Flatten
    pool = r.pop("pool")
    r.update(pool)

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
        basepool = await pool_snapshot(r["basePool"], chain, env, end_ts)
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
                "fee": int(Decimal(r["fee"]) * 10**10),
                "fee_mul": fee_mul,
                "admin_fee": int(Decimal(r["adminFee"]) * 10**10),
            },
            "coins": coins,
            "reserves": {
                "by_coin": normalized_reserves,
                "unnormalized_by_coin": unnormalized_reserves,
                "virtual_price": int(r["virtualPrice"]),
            },
            "basepool": basepool,
            "timestamp": int(r["timestamp"]),
        }
    else:
        if not isinstance(r["priceScale"], list):
            r["priceScale"] = [r["priceScale"]]
        if not isinstance(r["priceOracle"], list):
            r["priceOracle"] = [r["priceOracle"]]
        if not isinstance(r["lastPrices"], list):
            r["lastPrices"] = [r["lastPrices"]]

        ma_half_time = r["maHalfTime"]
        if ma_half_time:
            ma_half_time = int(ma_half_time)

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
                "ma_half_time": ma_half_time,
                "price_scale": [int(p) for p in r["priceScale"]],
                "price_oracle": [int(p) for p in r["priceOracle"]],
                "last_prices": [int(p) for p in r["lastPrices"]],
                "last_prices_timestamp": int(r["lastPricesTimestamp"]),
                "admin_fee": int(Decimal(r["adminFee"]) * 10**10),
                "xcp_profit": int(r["xcpProfit"]),
                "xcp_profit_a": int(r["xcpProfitA"]),
            },
            "coins": coins,
            "reserves": {
                "by_coin": normalized_reserves,
                "unnormalized_by_coin": unnormalized_reserves,
                "virtual_price": int(r["virtualPrice"]),
            },
            "basepool": basepool,
            "timestamp": int(r["timestamp"]),
        }

    return override_subgraph_data(data, "pool_snapshot", (address, chain))

convex_sync = sync(convex)
symbol_address_sync = sync(symbol_address)
pool_snapshot_sync = sync(pool_snapshot)

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
