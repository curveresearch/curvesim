"""
Network connector for Curve Prices API.
"""

from typing import List

from eth_utils import to_checksum_address
from pandas import DataFrame, to_datetime

from curvesim.exceptions import ApiResultError, CurvesimValueError

from .http import HTTP
from .utils import sync

URL = "https://prices.curve.fi/v1/"

CHAIN_ALIASES = {"mainnet": "ethereum"}


async def _get_pool_pair_volume(
    pool_address,
    base_token_address,
    quote_token_address,
    start_ts,
    end_ts,
    *,
    chain="ethereum",
    interval="day",
):
    chain = _chain_from_alias(chain)
    pool_address = to_checksum_address(pool_address)

    url = URL + f"volume/{chain}/{pool_address}"
    params = {
        "main_token": quote_token_address,
        "reference_token": base_token_address,
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
            f"Tokens: (base: {base_token_address}, quote: {quote_token_address}),\n"
            f"Timestamps: (start: {start_ts}, end: {end_ts})"
        ) from e

    return data


async def get_pool_pair_volume(
    pool_address: str,
    base_token_address: str,
    quote_token_address: str,
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

    base_token_address: str
        Address for the base token.

    quote_token_address: str
        Address for the quote token. Volumes are returned in units of

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
        base_token_address,
        quote_token_address,
        start_ts,
        end_ts,
        chain=chain,
        interval=interval,
    )

    df = DataFrame(data, columns=["timestamp", "volume", "fees"])
    df["timestamp"] = to_datetime(df["timestamp"], unit="s")
    df.set_index("timestamp", inplace=True)
    return df


def _chain_from_alias(chain):
    if chain in CHAIN_ALIASES:
        chain = CHAIN_ALIASES.get(chain, chain)

    if chain != "ethereum":
        raise CurvesimValueError(
            "Curve Prices API currently only supports Ethereum chain."
        )

    return chain


get_pool_pair_volume_sync = sync(get_pool_pair_volume)
