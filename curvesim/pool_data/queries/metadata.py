"""
Functions to get pool metadata for Curve pools.
"""
from typing import Optional, Union

from curvesim.constants import Chain
from curvesim.network.curve_prices import pool_snapshot_sync
# from curvesim.network.subgraph import pool_snapshot_sync, symbol_address_sync # TODO deprecate all?
from curvesim.network.web3 import underlying_coin_info_sync
from curvesim.pool_data.metadata import PoolMetaData, PoolMetaDataInterface
from curvesim.utils import Address, get_event_loop, to_address


def from_address(address: str, chain: str, end_ts: Optional[int] = None) -> dict:
    """
    Parameters
    ----------
    address: str
        Address prefixed with '0x'
    chain: str
        Chain name
    end_ts: Optional[int]
        TODO

    Returns
    -------
    Pool snapshot dictionary in the format returned by
    :func:`curvesim.network.curve_prices.pool_snapshot`.
    """
    loop = get_event_loop()
    data = pool_snapshot_sync(address, chain=chain, end_ts=end_ts, event_loop=loop)

    # Get underlying token addresses
    # if data["pool_type"] == "LENDING": # TODO deprecate?
    #     u_addrs, u_decimals = underlying_coin_info_sync(
    #         data["coins"]["addresses"], event_loop=loop
    #     )

    #     m = data.pop("coins")
    #     names = [n[1:] for n in m["names"]]

    #     data["coins"] = {
    #         "names": names,
    #         "addresses": u_addrs,
    #         "decimals": u_decimals,
    #         "wrapper": m,
    #     }

    return data


# def from_symbol(symbol, chain, env): # TODO deprecated?
#     address = symbol_address_sync(symbol, chain)

#     data = from_address(address, chain, env)

#     return data


def get_metadata(
    address: Union[str, Address],
    chain: Union[str, Chain] = Chain.MAINNET,
    end_ts: Optional[int] = None,
) -> PoolMetaDataInterface:
    """
    Pulls pool state and metadata from daily snapshot.

    Parameters
    ----------
    address : str, Address
        Pool address in proper checksum hexadecimal format.

    chain : str, Chain
        Chain/layer2 identifier, e.g. “mainnet”, “arbitrum”, “optimism".

    end_ts : Optional[int]
        Unix timestamp cutoff: the most recent snapshot before it will be pulled.
        The default value is the current datetime, which will pull the most recent snapshot.

    Returns
    -------
    :class:`~curvesim.pool_data.metadata.PoolMetaDataInterface`

    """
    address = to_address(address)
    chain = Chain(chain)

    metadata_dict = from_address(address, chain, end_ts=end_ts)
    metadata = PoolMetaData(metadata_dict)

    return metadata
