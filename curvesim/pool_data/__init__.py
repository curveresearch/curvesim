"""
Tools for fetching pool state and metadata.
Currently supports stableswap pools, meta-pools, and rebasing (RAI) metapools.
"""

__all__ = ["PoolDataCache", "from_address", "get_data_cache"]

from curvesim.pool_data.metadata import PoolMetaData

from .cache import PoolDataCache
from .queries import from_address


def get_data_cache(address, chain="mainnet", days=60, end=None):
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
    PoolData

    """
    # TODO: validate function arguments
    metadata_dict = from_address(address, chain)
    pool_data = PoolDataCache(metadata_dict, days=days, end=end)

    return pool_data


def get_metadata(address, chain="mainnet"):
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
    PoolData

    """
    # TODO: validate function arguments
    metadata_dict = from_address(address, chain)
    metadata = PoolMetaData(metadata_dict)

    return metadata
