Removed
-------
- Removed SimAssets type and SimPool.assets property
- Removed coin_names property from PricingMetrics
- Removed Coingecko pool_prices and coin_ids_from addresses


Added
-----
- Added DataSource, SimAsset, and TimeSequence template classes
- Added OnChainAsset and OnChainAssetPair as common SimAsset types
- Added DateTimeSequence for TimeSequences of datetimes
- Added get_asset_data() and get_pool_data() convenience functions to pipelines.common
- Added pool_data.get_pool_assets()
- Added CoinGeckoPriceVolumeSource and CsvDataSource in price_data.data_sources

Changed
-------
- Moved price/volume data retrieval outside of PriceVolume iterator
- Made explicit price and volume properties for PriceVolume iterator
- Changed Coingecko price data resampling to hourly samples with 10 minute tolerance
- Moved Coingecko resampling and DataFrame processing into CoinGeckoPriceVolumeSource
- Unified simple and volume-limited arbitrage pipeline interfaces
- Replaced pipeline arguments 'end_ts' & 'days' with 'time_sequence' & 'pool_ts'
- Renamed price_data.get() to price_data.get_price_data()
- Changed get_price_data() interface to use SimAsset, TimeSequence, and DataSource
- Replaced get_pool_volume() 'days' and 'end' arguments to 'start' and 'end'

Fixed
-----
- Fixed error in unit conversion for CoinGecko volume data. 
  Bug was introduced in commit df79810.


