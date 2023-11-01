"""
Functions to get pool metadata for Curve pools.
"""
from curvesim.network.subgraph import pool_snapshot_sync, symbol_address_sync
from curvesim.network.web3 import underlying_coin_info_sync
from curvesim.pool_data.metadata import PoolMetaData
from curvesim.utils import get_event_loop


def from_address(address, chain, env="prod", end_ts=None):
    """
    Returns

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
    data = pool_snapshot_sync(address, chain, env=env, end_ts=end_ts, event_loop=loop)

    # Get underlying token addresses
    if data["pool_type"] == "LENDING":
        u_addrs, u_decimals = underlying_coin_info_sync(
            data["coins"]["addresses"], event_loop=loop
        )

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
    address,
    chain="mainnet",
    env="prod",
    end_ts=None,
):
    """
    Pulls pool state and metadata from daily snapshot.

    Parameters
    ----------
    address : str
        Pool address prefixed with “0x”.

    chain : str
        Chain/layer2 identifier, e.g. “mainnet”, “arbitrum”, “optimism".

    Returns
    -------
    :class:`~curvesim.pool_data.metadata.PoolMetaDataInterface`

    """
    # TODO: validate function arguments
    metadata_dict = from_address(address, chain, env=env, end_ts=end_ts)
    metadata = PoolMetaData(metadata_dict)

    return metadata
