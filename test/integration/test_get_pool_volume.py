from curvesim.pipelines.vol_limited_arb.pool_volume import get_pool_volume
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
        volumes = get_pool_volume(pool_metadata, days=2, end=1698292800)
        assert len(volumes) == 2
        assert volumes.columns.to_list() == get_pairs(pool_metadata.coin_names)
