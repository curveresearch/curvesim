from curvesim.pool_data import get_pool_assets
from curvesim.pool_data.metadata import PoolMetaData
from curvesim.utils import get_pairs

from ..pool_metadata import (
    cryptopool_test_metadata,
    metapool_test_metadata,
    pool_test_metadata,
    tricrypto_ng_test_metadata,
)


def test_get_pool_assets():
    """Test get_pool_assets query."""
    metadata_list = [
        cryptopool_test_metadata,
        metapool_test_metadata,
        pool_test_metadata,
        tricrypto_ng_test_metadata,
    ]

    for metadata in metadata_list:
        pool_metadata = PoolMetaData(metadata)
        asset_pairs = get_pairs(pool_metadata.coin_names)

        # Test using metadata
        assets1 = get_pool_assets(pool_metadata)
        _pairs1 = [(asset.base.symbol, asset.quote.symbol) for asset in assets1]

        assert _pairs1 == asset_pairs

        # Test using address and chain
        address = pool_metadata.address
        chain = pool_metadata.chain
        assets2 = get_pool_assets(address, chain=chain)
        _pairs2 = [(asset.base.symbol, asset.quote.symbol) for asset in assets2]

        assert _pairs2 == asset_pairs
        assert assets1 == assets2
