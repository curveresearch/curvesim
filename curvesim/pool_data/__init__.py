"""
Tools for fetching pool state and metadata.

Currently supports stableswap pools, metapools, rebasing (RAI) metapools,
and 2-token cryptopools.
"""

__all__ = [
    "from_address",
    "get_data_cache",
    "get_metadata",
]

from typing import Optional, Union

from curvesim.constants import Chain, Env
from curvesim.pool_data.metadata import PoolMetaData
from curvesim.utils.address import Address, to_address

from .cache import PoolDataCache
from .queries import from_address


def get_data_cache(address, chain="mainnet", days=60, end=None):
    """
    Fetch historical volume and redemption price data and return
    in a cache object.

    Deprecation warning: this will likely be removed in a future release.

    Parameters
    ----------
    address : str
        Pool address prefixed with “0x”.

    chain : str
        Chain/layer2 identifier, e.g. “mainnet”, “arbitrum”, “optimism".

    Returns
    -------
    :class:`PoolDataCache`

    """
    # TODO: validate function arguments
    metadata_dict = from_address(address, chain, end_ts=end)
    pool_data = PoolDataCache(metadata_dict, days=days, end=end)

    return pool_data


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

    end_ts : int
        Posix timestamp

    Returns
    -------
    :class:`~curvesim.pool_data.metadata.PoolMetaDataInterface`

    """
    address = to_address(address)
    chain = Chain(chain)
    env = Env(env)

    metadata_dict = from_address(address, chain, env=env, end_ts=end_ts)
    metadata = PoolMetaData(metadata_dict)

    return metadata
