from curvesim.pool_data import get_pool_volume
from curvesim.pool_data.metadata import PoolMetaData
from curvesim.utils import get_pairs

from ..unit.test_pool_metadata import (
    cryptopool_test_metadata,
    metapool_test_metadata,
    pool_test_metadata,
    tricrypto_ng_test_metadata,
)


def test_get_pool_volume():
    """Test the volume query."""
    metadata_list = [
        cryptopool_test_metadata,
        metapool_test_metadata,
        pool_test_metadata,
        tricrypto_ng_test_metadata,
    ]

    for metadata in metadata_list:
        pool_metadata = PoolMetaData(metadata)

        # Test using metadata
        volumes1 = get_pool_volume(pool_metadata, days=2, end=1698292800)
        assert len(volumes1) == 2
        assert volumes1.columns.to_list() == get_pairs(pool_metadata.coin_names)

        # Test using address and chain
        address = pool_metadata.address
        chain = pool_metadata.chain
        volumes2 = get_pool_volume(address, chain=chain, days=2, end=1698292800)
        assert len(volumes2) == 2
        assert volumes2.columns.to_list() == get_pairs(pool_metadata.coin_names)

        assert all(volumes1 == volumes2)
