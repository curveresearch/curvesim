Added
-----

- `curvesim.pool.get` can now be used to fetch and instantiate cryptopools.
- `curvesim` now uses python logging with log levels.  This allows for debug logging and
  saving logs to files.

Changed
-------

- By default, pool instantiation will now create balances in native token units.
  Previously it had normalized to 18 decimals.  This option still exists but must
  now be chosen explicitly.
- Some internal objects used by `curvesim` were refactored for better maintainability,
  namely `PoolData` is now split into `PoolDataCache` and `PoolMetaData`.


Fixed
-----

- Timezone issue in subgraph queries.
