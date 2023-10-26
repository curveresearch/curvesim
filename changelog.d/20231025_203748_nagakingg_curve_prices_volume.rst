Removed
-------
- Removed volume multiplier modes
- Removed pipelines.utils
- Removed PriceVolume.total_volumes()
- Removed volume from PoolDataCache
- Removed convex subgraph volume query
- Removed PoolDataCache

Added
-----
- Added network.curve_prices
- Added ApiResultError to exceptions
- Added vol_limited_arb.pool_volume.get_pool_volume()

Changed
-------
- Volume multipliers now computed individually for each asset pair
