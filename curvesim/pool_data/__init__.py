"""
Tools for fetching pool state and metadata.
Currently supports stableswap pools, meta-pools, and rebasing (RAI) metapools.
"""

__all__ = ["PoolDataCache", "from_address", "from_symbol", "get_data_cache"]

from curvesim.pool_data.metadata import PoolMetaData

from .cache import PoolDataCache
from .queries import from_address, from_symbol


def get_data_cache(address_or_symbol, chain="mainnet", days=60, end=None):
    """
    Pulls pool state and metadata from daily snapshot.

    Parameters
    ----------
    address_or_symbol : str
        Pool address prefixed with “0x” or LP token symbol.

    chain : str
        Chain/layer2 identifier, e.g. “mainnet”, “arbitrum”, “optimism".

    Returns
    -------
    PoolData

    """
    # TODO: validate function arguments
    if address_or_symbol.startswith("0x"):
        from_x = from_address
    else:
        from_x = from_symbol

    metadata_dict = from_x(address_or_symbol, chain)
    pool_data = PoolDataCache(metadata_dict, days=days, end=end)

    return pool_data


def get_metadata(address_or_symbol, chain="mainnet"):
    """
    Pulls pool state and metadata from daily snapshot.

    Parameters
    ----------
    address_or_symbol : str
        Pool address prefixed with “0x” or LP token symbol.

    chain : str
        Chain/layer2 identifier, e.g. “mainnet”, “arbitrum”, “optimism".

    Returns
    -------
    PoolData

    """
    # TODO: validate function arguments
    if address_or_symbol.startswith("0x"):
        from_x = from_address
    else:
        from_x = from_symbol

    metadata_dict = from_x(address_or_symbol, chain)
    metadata = PoolMetaData(metadata_dict)

    return metadata
