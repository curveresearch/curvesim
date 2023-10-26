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
- Added Curve Prices API volume query (network.curve_prices)
- Added pool_data.get_pool_volume() to fetch historical pool volume from
  Curve Prices API

Changed
-------
- Volume multipliers now computed individually for each asset pair
- Replaced pool_data.queries with folder
- Pool volume and volume limiting are only supported for Ethereum pools 
  pending updates to Curve Prices API

Deprecated
----------
- RAI3CRV pool is currently unsupported by simulation pipelines. It will
  be reimplemented along with Stableswap-NG pools. 

