from datetime import datetime, timezone

from eth_utils import to_checksum_address

from curvesim.exceptions import ApiResultError, CurvesimValueError

from .http import HTTP
from .utils import sync

URL = "https://prices.curve.fi/v1/"

CHAIN_ALIASES = {"mainnet": "ethereum"}


async def _get_pool_parameters(address, chain="ethereum", start_ts=None, end_ts=None):
    if chain in CHAIN_ALIASES:
        chain = CHAIN_ALIASES[chain]

    if chain != "ethereum":
        raise CurvesimValueError(
            "Parameter snapshots are currently only available for the Ethereum chain."
        )

    address = to_checksum_address(address)
    end_ts = end_ts or int(datetime.now(timezone.utc).timestamp())
    start_ts = start_ts or end_ts - 86400

    url = URL + f"snapshots/{chain}/{address}"
    params = {"start": start_ts, "end": end_ts}
    r = await HTTP.get(url, params=params)

    try:
        r = r["data"][0]
    except IndexError as e:
        raise ApiResultError(
            f"No pool parameters returned for pool: {address}, {chain}"
        ) from e

    return r


get_pool_parameters = sync(_get_pool_parameters)
