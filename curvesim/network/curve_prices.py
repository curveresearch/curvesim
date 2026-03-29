"""
Network connector for Curve Prices API.
"""

from time import time
from typing import Any, Dict, List, Optional

from eth_utils import to_checksum_address
from pandas import DataFrame, to_datetime

from curvesim.exceptions import ApiResultError

from .http import HTTP
from .utils import sync

URL = "https://prices.curve.finance/v1/"

CHAIN_ALIASES = {
    "mainnet": "ethereum",
    "matic": "polygon",
}


async def _get_pool_pair_volume(
    pool_address,
    main_token_address,
    reference_token_address,
    start_ts,
    end_ts,
    *,
    chain="ethereum",
    interval="day",
):
    chain = _chain_from_alias(chain)
    pool_address = to_checksum_address(pool_address)
    main_token_address = to_checksum_address(main_token_address)
    reference_token_address = to_checksum_address(reference_token_address)

    url = URL + f"volume/{chain}/{pool_address}"
    params = {
        "main_token": main_token_address,
        "reference_token": reference_token_address,
        "start": start_ts,
        "end": end_ts,
        "interval": interval,
    }
    r = await HTTP.get(url, params=params)

    try:
        data = r["data"]
    except KeyError as e:
        raise ApiResultError(
            "No historical volume returned for\n"
            f"Pool: '{pool_address}', Chain: '{chain}',\n"
            f"Tokens: (main: {main_token_address}, "
            f"reference: {reference_token_address}),\n"
            f"Timestamps: (start: {start_ts}, end: {end_ts})"
        ) from e

    return data


async def get_pool_pair_volume(
    pool_address: str,
    main_token_address: str,
    reference_token_address: str,
    start_ts: int,
    end_ts: int,
    *,
    chain: str = "ethereum",
    interval: str = "day",
) -> DataFrame:
    """
    Gets historical daily volume for a pair of coins traded in a Curve pool.

    Parameters
    ----------
    pool_address: str
        The Curve pool's address.

    main_token_address: str
        Address for the token volume will be denominated in.

    reference_token_address: str
        Address for the second token in the trading pair.

    start_ts: int
        Posix timestamp (UTC) for start of query period.

    end_ts: int
        Posix timestamp (UTC) for end of query period.

    chain: str, default "ethereum"
        The pool's blockchain (note: currently only "ethereum" supported)

    interval: str, default "day"
        The sampling interval for the data. Available values: week, day, hour

    Returns
    -------
    DataFrame
        Rows: DateTimeIndex; Columns: volume, fees

    """
    data: List[dict] = await _get_pool_pair_volume(
        pool_address,
        main_token_address,
        reference_token_address,
        start_ts,
        end_ts,
        chain=chain,
        interval=interval,
    )

    df = DataFrame(data, columns=["timestamp", "volume", "fees"], dtype="float64")
    df["timestamp"] = to_datetime(df["timestamp"], unit="s")
    df.set_index("timestamp", inplace=True)
    return df


async def _pool_metadata(address: str, chain: str) -> Dict:
    chain = _chain_from_alias(chain)
    address = to_checksum_address(address)
    url = URL + f"pools/{chain}/{address}/metadata"
    return await HTTP.get(url)


async def _pool_snapshots(
    address: str, chain: str, start_ts: int, end_ts: int
) -> List[Dict]:
    chain = _chain_from_alias(chain)
    address = to_checksum_address(address)
    url = URL + f"snapshots/{chain}/{address}"
    params = {"start": start_ts, "end": end_ts}
    response = await HTTP.get(url, params=params)
    return response["data"]


async def _pool_tvl_snapshots(
    address: str, chain: str, start_ts: int, end_ts: int, unit: str = "day"
) -> List[Dict]:
    chain = _chain_from_alias(chain)
    address = to_checksum_address(address)
    url = URL + f"snapshots/{chain}/{address}/tvl"
    params = {"start": start_ts, "end": end_ts, "unit": unit}
    response = await HTTP.get(url, params=params)
    return response["data"]


async def pool_snapshot(
    address: str, chain: str = "ethereum", end_ts: Optional[int] = None
) -> Dict:
    """
    Pulls pool metadata and the latest snapshot from the current Curve API.

    Parameters
    ----------
    address : str
        Pool address.

    chain : str, default="ethereum"
        Chain name or alias.

    end_ts : int, optional
        Unix timestamp cutoff. The latest snapshot at or before this timestamp
        will be used.

    Returns
    -------
    dict
        Pool metadata in the same general shape returned by the subgraph helper.
    """
    if end_ts is None:
        end_ts = int(time())

    # The Curve API serves recent snapshots, but not every chain/pool has dense
    # historical coverage. A one-week window is enough to grab a recent point
    # while still respecting the caller's cutoff.
    start_ts = max(end_ts - 7 * 24 * 60 * 60, 0)
    meta = await _pool_metadata(address, chain)
    snapshots = await _pool_snapshots(address, chain, start_ts, end_ts)
    tvl_snapshots = await _pool_tvl_snapshots(address, chain, start_ts, end_ts)

    if not snapshots or not tvl_snapshots:
        raise ApiResultError(
            f"No pool snapshot returned for pool '{address}' on chain '{chain}'."
        )

    latest_snapshot = snapshots[0]
    latest_tvl = tvl_snapshots[0]

    sorted_coins = sorted(meta["coins"], key=lambda coin: coin["pool_index"])
    balance_count = len(latest_tvl["balances"])

    basepool = None
    wrapper: Optional[Dict[str, Any]] = None

    if meta["metapool"]:
        selected_coins = sorted_coins[:balance_count]
        basepool = await pool_snapshot(meta["base_pool"], chain=chain, end_ts=end_ts)
    elif len(sorted_coins) == 2 * balance_count:
        wrapper_coins = sorted_coins[:balance_count]
        selected_coins = sorted_coins[balance_count:]
        wrapper = {
            "names": [coin["symbol"] for coin in wrapper_coins],
            "addresses": [
                to_checksum_address(coin["address"]) for coin in wrapper_coins
            ],
            "decimals": [coin["decimals"] for coin in wrapper_coins],
        }
    else:
        selected_coins = sorted_coins[:balance_count]

    coins: Dict[str, Any] = {
        "names": [coin["symbol"] for coin in selected_coins],
        "addresses": [to_checksum_address(coin["address"]) for coin in selected_coins],
        "decimals": [coin["decimals"] for coin in selected_coins],
    }
    if wrapper:
        coins["wrapper"] = wrapper

    normalized_reserves = []
    unnormalized_reserves = []
    for balance, coin in zip(latest_tvl["balances"], selected_coins):
        unnormalized = int(balance * 10 ** coin["decimals"])
        unnormalized_reserves.append(unnormalized)
        normalized_reserves.append(unnormalized * 10 ** (18 - coin["decimals"]))

    data = {
        "name": meta["name"],
        "address": to_checksum_address(address),
        "chain": chain if chain not in CHAIN_ALIASES else chain,
        "symbol": meta["name"],
        "version": 2 if latest_snapshot["gamma"] is not None else 1,
        "pool_type": _pool_type(meta, latest_snapshot),
        "params": _pool_params(latest_snapshot, latest_tvl),
        "coins": coins,
        "reserves": {
            "by_coin": normalized_reserves,
            "unnormalized_by_coin": unnormalized_reserves,
            "virtual_price": int(latest_snapshot["virtual_price"]),
        },
        "basepool": basepool,
        "timestamp": int(latest_tvl["timestamp"]),
    }

    return data


def _pool_type(meta: Dict, snapshot: Dict) -> str:
    if meta["metapool"]:
        return "METAPOOL_FACTORY" if meta["registry_type"] == "factory" else "METAPOOL"

    if snapshot["gamma"] is not None:
        pool_type = meta["pool_type"]
        return {
            "crypto": "REGISTRY_V2",
            "factory_crypto": "CRYPTO_FACTORY",
            "factory_tricrypto": "TRICRYPTO_FACTORY",
            "twocryptong": "TWOCRYPTO_NG",
        }.get(pool_type, pool_type.upper())

    sorted_coins = sorted(meta["coins"], key=lambda coin: coin["pool_index"])
    if len(sorted_coins) % 2 == 0:
        first_half = [coin["symbol"] for coin in sorted_coins[: len(sorted_coins) // 2]]
        second_half = [
            coin["symbol"] for coin in sorted_coins[len(sorted_coins) // 2 :]
        ]
        if all(
            wrapper.endswith(underlying)
            for wrapper, underlying in zip(first_half, second_half)
        ):
            return "LENDING"

    return "STABLE_FACTORY" if meta["registry_type"] == "factory" else "REGISTRY_V1"


def _pool_params(snapshot: Dict, tvl_snapshot: Dict) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "A": int(snapshot["a"]),
        "admin_fee": int(snapshot["admin_fee"]),
    }

    if snapshot["gamma"] is None:
        offpeg = snapshot["offpeg_fee_multiplier"]
        params.update(
            {
                "fee": int(snapshot["fee"]),
                "fee_mul": int(offpeg) if offpeg is not None else None,
            }
        )
        return params

    derived_prices = _derived_crypto_prices(snapshot, tvl_snapshot)
    params.update(
        {
            "gamma": int(snapshot["gamma"]),
            "fee_gamma": int(snapshot["fee_gamma"]),
            "mid_fee": int(snapshot["mid_fee"]),
            "out_fee": int(snapshot["out_fee"]),
            "allowed_extra_profit": int(snapshot["allowed_extra_profit"]),
            "adjustment_step": int(snapshot["adjustment_step"]),
            "ma_half_time": int(snapshot["ma_half_time"]),
            "price_scale": derived_prices,
            "price_oracle": derived_prices,
            # The current API exposes live scale/oracle values but not the
            # separate last_prices fields that older subgraph snapshots returned.
            "last_prices": derived_prices,
            "last_prices_timestamp": int(snapshot["timestamp"]),
            "xcp_profit": int(snapshot["xcp_profit"]),
            "xcp_profit_a": int(snapshot["xcp_profit_a"]),
        }
    )

    return params


def _derived_crypto_prices(snapshot: Dict, tvl_snapshot: Dict) -> List[int]:
    if snapshot["price_scale"] is not None:
        return [int(price) for price in snapshot["price_scale"]]

    token_prices = tvl_snapshot["token_prices"]
    if not token_prices:
        raise ApiResultError("No token prices available for cryptoswap snapshot.")

    base_price = token_prices[0]
    return [int(price * 10**18 / base_price) for price in token_prices[1:]]


def _chain_from_alias(chain):
    if chain in CHAIN_ALIASES:  # pylint: disable=consider-using-get
        chain = CHAIN_ALIASES[chain]

    return chain


pool_snapshot_sync = sync(pool_snapshot)
get_pool_pair_volume_sync = sync(get_pool_pair_volume)
