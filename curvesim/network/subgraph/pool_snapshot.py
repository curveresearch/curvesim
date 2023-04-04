from eth_utils.address import to_checksum_address

from curvesim.exceptions import SubgraphResultError


def pool_snapshot_query(address):
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
            offPegFeeMultiplier
            reserves
            normalizedReserves
            virtualPrice
            timestamp
          }
        }
    """
        % address.lower()
    )
    return q


def process_pool_snapshot_result(r):
    try:
        r = r["dailyPoolSnapshots"][0]
    except IndexError:
        raise SubgraphResultError(
            f"No daily snapshot for this pool: {address}, {chain}"
        )

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
        basepool = await self.pool_snapshot(r["basePool"])
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
            "by_coin": normalized_reserves,
            "unnormalized_by_coin": unnormalized_reserves,
            "virtual_price": int(r["virtualPrice"]),
            "tokens": D * 10**18 // int(r["virtualPrice"]),
        },
        "basepool": None,
        "timestamp": int(r["timestamp"]),
    }

    return override_subgraph_data(data, "pool_snapshot", (address, chain))
