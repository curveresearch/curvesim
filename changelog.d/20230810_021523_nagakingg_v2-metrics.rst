Added
-----
- Add get_pool_parameters and get_pool_state functions for SimCurveCryptoPool
- incorporate SimCurveCryptoPool into PoolVolume, PoolBalance, PoolValue metrics
- Activate ParameterizedCurveCryptoPoolIterator tests
- test initialization, attributes, properties, methods of each metric type

Changed
-------
- Slight reorganization of metric configs/methods to minimize duplication
- Update metrics.PricingMixin to support price dicts
- add unmapped pool exception to get_pool_state/get_pool_parameters
- cache PoolMetric.pool_config for better testing
