"""
Network connector for Curve Prices API.
"""

from time import time
from typing import List, Dict, Optional

from eth_utils import to_checksum_address
from pandas import DataFrame, to_datetime

from curvesim.logging import get_logger
from curvesim.exceptions import ApiResultError, CurvesimValueError

from .http import HTTP
from .utils import sync

logger = get_logger(__name__)

URL = "https://prices.curve.fi/v1/"

CHAIN_ALIASES = {
    "mainnet": "ethereum",
    "matic": "polygon",
}

REVERSE_CHAIN_ALIASES = {alias: chain for chain, alias in CHAIN_ALIASES.items()}


async def _get_pool_pair_volume(
    pool_address,
    main_token_address,
    reference_token_address,
    start_ts,
    end_ts,
    *,
    chain="ethereum",
    interval="day",
) -> List[Dict]:
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

    data: List[Dict] = r["data"]
    if data == []:
        raise ApiResultError(
            "No historical volume returned for\n"
            f"Pool: '{pool_address}', Chain: '{chain}',\n"
            f"Tokens: (main: {main_token_address}, "
            f"reference: {reference_token_address}),\n"
            f"Timestamps: (start: {start_ts}, end: {end_ts})"
        )

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


async def _pool_metadata(address, chain) -> Dict:
    """"""
    chain = _chain_from_alias(chain)
    address = to_checksum_address(address)
    url = URL + f"pools/{chain}/{address}/metadata"

    r = await HTTP.get(url)
    data: dict = r

    # TODO - see _get_pool_pair_volume
    if data["vyper_version"] == None or data["deployment_tx"] == None or data["deployment_block"] == None:
        raise ApiResultError()

    return data


async def _pool_parameters(address, chain, start_ts, end_ts) -> List[Dict]:
    """"""
    chain = _chain_from_alias(chain)
    address = to_checksum_address(address)
    url = URL + f"snapshots/{chain}/{address}"
    params = {"start": start_ts, "end": end_ts}

    r = await HTTP.get(url, params=params)

    data: List[Dict] = r["data"]
    if data == []:
        # TODO
        raise ApiResultError("pass\n" f"Timestamps: (start: {start_ts}, end: {end_ts})")

    return data


async def _pool_balances(address, chain, start_ts, end_ts, unit="day") -> List[Dict]:
    """"""
    chain = _chain_from_alias(chain)
    address = to_checksum_address(address)
    url = URL + f"snapshots/{chain}/{address}/tvl"
    params = {"start": start_ts, "end": end_ts, "unit": unit}

    r = await HTTP.get(url, params=params)

    data: list[dict] = r["data"]
    if data == []:
        # TODO
        raise ApiResultError("pass\n" f"Timestamps: (start: {start_ts}, end: {end_ts})")

    return data


async def pool_snapshot(address: str, chain: str = "ethereum", end_ts: Optional[int] = None) -> Dict:
    """"""
    if end_ts == None:
        end_ts = int(time())

    snapshot_start = end_ts - (24 * 60 * 60)
    snapshot_end = end_ts

    pool_metadata: Dict = await _pool_metadata(address, chain)
    params_snapshot: List[Dict] = await _pool_parameters(address, chain, snapshot_start, snapshot_end)
    balances_snapshot: List[Dict] = await _pool_balances(address, chain, snapshot_start, snapshot_end)

    latest_snapshot: Dict = params_snapshot[0]
    latest_balances: Dict = balances_snapshot[0]

    if pool_metadata["metapool"]:
        # metapools currently only contain one token paired with their basepool's LP token (2 total)
        # however, curve-prices lumps metapool tokens with basepool tokens
        coins_in_pool: list[dict] = pool_metadata["coins"][:2]
        basepool = await pool_snapshot(pool_metadata["base_pool"], chain=chain, end_ts=end_ts)
    else:
        coins_in_pool: list[dict] = pool_metadata["coins"]
        basepool = None

    coins: Dict[str, list] = {"names": [], "addresses": [], "decimals": []}

    for info_dict in coins_in_pool:
        coins["names"].append(info_dict["symbol"])
        coins["addresses"].append(to_checksum_address(info_dict["address"]))
        coins["decimals"].append(info_dict["decimals"])

    normalized_reserves: list[int] = []
    unnormalized_reserves: list[int] = []

    for balance, decimals in zip(latest_balances["balances"], coins["decimals"]):
        normalized_reserves.append(int(balance * 10**18))
        unnormalized_reserves.append(int(balance * 10**decimals))

    data = {
        "name": pool_metadata["name"],
        "address": to_checksum_address(address),
        "chain": chain if not chain in REVERSE_CHAIN_ALIASES else REVERSE_CHAIN_ALIASES[chain],
        "symbol": pool_metadata["name"],
        "pool_type": pool_metadata["pool_type"],
        "params": {},
        "coins": coins,
        "reserves": {
            "by_coin": normalized_reserves,
            "unnormalized_by_coin": unnormalized_reserves,
        },
        "basepool": basepool,
        "timestamp": end_ts,
    }

    if pool_type_to_amm[data["pool_type"]] == "stableswap":
        fee_mul = latest_snapshot["offpeg_fee_multiplier"]

        params = {
            "A": int(latest_snapshot["a"]),
            "fee": int(latest_snapshot["fee"]),
            "fee_mul": int(fee_mul) if fee_mul != None else None,
            "admin_fee": int(latest_snapshot["admin_fee"]),
            "virtual_price": int(latest_snapshot["virtual_price"]),
        }
        data["params"].update(params)

    elif pool_type_to_amm[data["pool_type"]] == "cryptoswap":
        token_price_base: float = latest_balances["token_prices"][0]
        last_prices: list[int] = [int(usd * 10**18 / token_price_base) for usd in latest_balances["token_prices"][1:]]
        last_prices_timestamp: int = int(latest_balances["timestamp"])

        params = {
            "A": int(latest_snapshot["a"]),
            "gamma": int(latest_snapshot["gamma"]),
            "fee_gamma": int(latest_snapshot["fee_gamma"]),
            "mid_fee": int(latest_snapshot["mid_fee"]),
            "out_fee": int(latest_snapshot["out_fee"]),
            "allowed_extra_profit": int(latest_snapshot["allowed_extra_profit"]),
            "adjustment_step": int(latest_snapshot["adjustment_step"]),
            "ma_half_time": int(latest_snapshot["ma_half_time"]),
            "price_scale": [int(p) for p in latest_snapshot["price_scale"]],
            "price_oracle": [int(p) for p in latest_snapshot["price_oracle"]],
            "last_prices": last_prices,
            "last_prices_timestamp": last_prices_timestamp,
            "admin_fee": int(latest_snapshot["admin_fee"]),
            "xcp_profit": int(latest_snapshot["xcp_profit"]),
            "xcp_profit_a": int(latest_snapshot["xcp_profit_a"]),
            "virtual_price": int(latest_snapshot["virtual_price"]),
        }
        data["params"].update(params)

    else:
        raise ApiResultError(
            f"Pulling snapshots for non-Stableswap or non-Cryptoswap pools is not yet supported. Pool type: \"{data['pool_type']}\""
        )

    logger.debug("Pool snapshot: %s", str(data))

    return data


def _chain_from_alias(chain):
    if chain in CHAIN_ALIASES:  # pylint: disable=consider-using-get
        chain = CHAIN_ALIASES[chain]

    return chain


pool_type_to_amm: Dict[str, Optional[str]] = {
    "main": "stableswap",
    "crypto": "cryptoswap",
    "factory": "stableswap",
    "factory_crypto": "cryptoswap",
    "crvusd": None,
    "factory_tricrypto": "cryptoswap",
    "stableswapng": "stableswap",
    "twocryptong": "cryptoswap",
}
pool_snapshot_sync = sync(pool_snapshot)  # TODO export?
get_pool_pair_volume_sync = sync(get_pool_pair_volume)
