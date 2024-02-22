"""
Functions to get assets for Curve pools.
"""

from typing import List, Union

from curvesim.constants import Chain
from curvesim.pool_data.metadata import PoolMetaDataInterface
from curvesim.pool_data.queries.metadata import get_metadata
from curvesim.templates import OnChainAsset, OnChainAssetPair
from curvesim.utils import get_pairs


def get_pool_assets(
    metadata_or_address, chain: Union[str, Chain] = Chain.MAINNET
) -> List[OnChainAssetPair]:
    """
    Gets asset pairs tradeable for the specified pool.

    Parameters
    ----------
    metadata_or_address: PoolMetaDataInterface or str
        Pool metadata or pool address to fetch metadata.

    chain: str or Chain, default=Chain.MAINNET
        Chain to use if pool address is provided to fetch metadata.

    Returns
    -------
    List[OnChainAssetPair]

    """
    if isinstance(metadata_or_address, str):
        pool_metadata: PoolMetaDataInterface = get_metadata(metadata_or_address, chain)
    else:
        pool_metadata = metadata_or_address

    symbol_pairs = get_pairs(pool_metadata.coin_names)
    address_pairs = get_pairs(pool_metadata.coins)

    sim_assets = []
    for pair_info in zip(symbol_pairs, symbol_pairs, address_pairs):
        base_info, quote_info = tuple(zip(*pair_info))

        base_asset = OnChainAsset(*base_info, pool_metadata.chain)  # type: ignore [call-arg]
        quote_asset = OnChainAsset(*quote_info, pool_metadata.chain)  # type: ignore [call-arg]

        asset_pair = OnChainAssetPair(base_asset, quote_asset)
        sim_assets.append(asset_pair)

    return sim_assets
