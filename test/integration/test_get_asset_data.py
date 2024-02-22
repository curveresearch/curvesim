import os

from curvesim.pipelines.common import get_asset_data
from curvesim.pool_data.metadata import PoolMetaData
from curvesim.utils import get_pairs

from ..pool_metadata import metapool_test_metadata


def test_get_asset_data():
    """
    Tests interworking of SimAssets, TimeSequence, DataSource, and associated functions:
    get_asset_data(), get_pool_assets(), and get_price_data()
    """

    pool_metadata = PoolMetaData(metapool_test_metadata)
    asset_pairs = get_pairs(pool_metadata.coin_names)

    # Test with default TimeSequence and DataSource
    asset_data, time_sequence = get_asset_data(pool_metadata, None, "coingecko")

    assert len(time_sequence) == 1440  # default 60-day sequence
    assert all(asset_data.index == time_sequence)
    assert all(asset_data["price"].columns == asset_pairs)
    assert all(asset_data["volume"].columns == asset_pairs)

    # Save data and test local DataSource
    symbols = asset_data.columns.get_level_values("symbol").unique()
    for symbol in symbols:
        df = asset_data.xs(symbol, level="symbol", axis=1)
        df.to_csv("-".join(symbol) + ".csv")

    asset_data_local, time_sequence_local = get_asset_data(pool_metadata, None, "local")

    price_diff = (asset_data["price"] - asset_data_local["price"]).abs()
    volume_diff = (asset_data["volume"] - asset_data_local["volume"]).abs()

    assert price_diff.max().max() < 1e-10
    assert volume_diff.max().max() < 1e-3
    assert all([a == b for a, b in zip(time_sequence, time_sequence_local)])

    # Clean up
    for symbol in symbols:
        os.remove("-".join(symbol) + ".csv")
