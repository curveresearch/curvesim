"""
Functions to get pool metadata for Curve pools.
"""

from typing import Optional, Union

from curvesim.constants import Chain, Env
from curvesim.network.subgraph import symbol_address_sync
from curvesim.network.subgraph import pool_snapshot_sync as pool_snapshot_sync_subgraph
from curvesim.network.curve_prices import pool_snapshot_sync as pool_snapshot_sync_curve_prices
from curvesim.network.web3 import underlying_coin_info_sync
from curvesim.pool_data.metadata import PoolMetaData
from curvesim.utils import Address, get_event_loop, to_address
from ...logging import get_logger

logger = get_logger(__name__)


def from_address(address, chain, env="prod", end_ts=None):
    """
    Parameters
    ----------
    address: str
        Address prefixed with '0x'
    chain: str
        Chain name
    env: str
        Environment name for subgraph: 'prod' or 'staging'

    Returns
    -------
    Pool snapshot dictionary in the format returned by
    :func:`curvesim.network.subgraph.pool_snapshot`.
    """
    loop = get_event_loop()
    try:
        data = pool_snapshot_sync_subgraph(address, chain, env=env, end_ts=end_ts, event_loop=loop)
    except Exception as e:
        # If subgraph fails, try Curve Prices API
        logger.info(f"Subgraph failed with error: {e}, trying Curve Prices API")
        data = pool_snapshot_sync_curve_prices(address, chain, end_ts=end_ts, event_loop=loop)

    # Get underlying token addresses
    if data["pool_type"] == "LENDING":
        u_addrs, u_decimals = underlying_coin_info_sync(data["coins"]["addresses"], event_loop=loop)

        m = data.pop("coins")
        names = [n[1:] for n in m["names"]]

        data["coins"] = {
            "names": names,
            "addresses": u_addrs,
            "decimals": u_decimals,
            "wrapper": m,
        }

    return data


def from_symbol(symbol, chain, env):
    address = symbol_address_sync(symbol, chain)

    data = from_address(address, chain, env)

    return data


def get_metadata(
    address: Union[str, Address],
    chain: Union[str, Chain] = Chain.MAINNET,
    env: Union[str, Env] = Env.PROD,
    end_ts: Optional[int] = None,
):
    """
    Pulls pool state and metadata from daily snapshot.

    Parameters
    ----------
    address : str, Address
        Pool address in proper checksum hexadecimal format.

    chain : str, Chain
        Chain/layer2 identifier, e.g. “mainnet”, “arbitrum”, “optimism".

    end_ts : int, optional
        Datetime cutoff, given as Unix timestamp, to pull last snapshot before.
        The default value is current datetime, which will pull the most recent snapshot.

    Returns
    -------
    :class:`~curvesim.pool_data.metadata.PoolMetaDataInterface`

    """
    address = to_address(address)
    chain = Chain(chain)
    env = Env(env)

    metadata_dict = from_address(address, chain, env=env, end_ts=end_ts)
    metadata = PoolMetaData(metadata_dict)
    metadata = _validate_metadata(metadata)
    return metadata


def _validate_metadata(pool_metadata):
    coins_address = [
        "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2" if coin == "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE" else coin
        for coin in pool_metadata.coins
    ]
    coin_names = ["WETH" if name == "0xeeee" else name for name in pool_metadata.coin_names]
    pool_metadata._dict["coins"]["addresses"] = coins_address
    pool_metadata._dict["coins"]["names"] = coin_names
    return pool_metadata
