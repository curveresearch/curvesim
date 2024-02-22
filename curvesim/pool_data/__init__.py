"""
Tools for fetching pool metadata and volume.

Currently supports stableswap pools, metapools, rebasing (RAI) metapools,
and 2-token cryptopools.
"""

__all__ = ["get_metadata", "get_pool_assets", "get_pool_volume"]


from .queries.metadata import get_metadata
from .queries.pool_assets import get_pool_assets
from .queries.pool_volume import get_pool_volume
