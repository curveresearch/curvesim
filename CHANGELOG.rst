
.. _changelog-0.4.0:

0.4.0 — 2023-06-29
==================

The v0.4.5 milestone incoporated many cleanups and refactorings for improved readability and maintability in preparation for the cryptosim milestone.  We highlight the main ones below.

Removed
-------

- Unused Nomics wrapper and Coingecko code was removed.
- Old references to "freq" attribute from price sampler were removed (#118).

Added
-----

- Python 3.11 is now officially supported.
- Advanced custom metrics support (#117).
- SimPools now support token symbols for trade, price, and balances (#131, #150)
- CI now tests a matrix of OS and supported Python versions (#134)
- A simple pipeline was added to enable faster CI tests and serve as an easy example (#132).
- Integrated SimAssets into SimPools for simpler handling (#131).
- New classes Trade and TradeResult for better simulation results tracking.
- Support specifying end date when pulling data from Coingecko.
- Snapshot timestamp is now incorporated into metadata fetch (#133).

Fixed
-----

- Corrected layer 2 addresses in pool metadata (#130).

Improved
--------

- An updated README and the docs, especially for advanced metrics and strategies.
- Multiple changes to simplify and conform to simulation interfaces.
- Defensive check for sim pool precisions was added (#126).
- Refactored SimStableswapBase into a mixin for better modularity (#146).
- ArbMetric updated for better numerical stability (#137).
- Python-native types are now used in price_sampler, pool_data, pipeline (#137).

.. _changelog-0.4.0:

0.4.0 — 2023-05-19
==================

Removed
-------

- Nomics market data is no longer available, so we have removed all nomics related functionality.
- Removed pool lp token symbol lookup when creating pools from on-chain data.
- Standalone functions for AMM logic are removed.  This eases the testing burden
  without impacting performance (due to other changes such as `__slot__` usage).
- The matplotlib results plotter was replaced with an altair plotter.


Added
-----

- Curve pool types now use `__slots__` for more performant attribute access.
- Revamped pool hierarchy so that the implementations of `SimPool` derive
  from Curve pools and `SimStableSwapBase`, which better organizes common
  logic across stableswap sim pool types and decouples sim logic from the
  core AMM pools.
- Pools now have a revert-to-snapshot functionality.
- Add `CurveCryptoPool`, a python implementation of the vyper factory
  cryptoswap pool.
- `curvesim.pool.get` can now be used to fetch and instantiate cryptopools.
- `curvesim` now uses python logging with log levels.  This allows for debug logging and
  saving logs to files.
- Altair results plotter added to improve readability and support flexible plotting (e.g., across pool types)
- Metrics submodule added to facilitate simulation metric development.


Changed
-------

- `CurveMetaPool` uses `rate_multiplier` as in the vyper logic instead of `p`
- By default, pool instantiation will now create balances in native token units.
  Previously it had normalized to 18 decimals.  This option still exists but must
  now be chosen explicitly.
- Some internal objects used by `curvesim` were refactored for better maintainability,
  namely `PoolData` is now split into `PoolDataCache` and `PoolMetaData`.


Fixed
-----

- Use `rates` property consistently across stableswap types
- Add error handling for convex subgraph
- Timezone issue in subgraph queries.


.. _changelog-0.3.0:

0.3.0 — 2022-11-08
==================


Added
-----

- Multi-chain pool data support via the Convex Community subgraph.

- New network subpackage uses `asyncio` for concurrency.

- Pool_data and price_data submodules added.

- Single cpu-mode (`ncpu=1`) will run in a single process without the `multiprocessing`
  library.  This makes it easier to profile using tools like `cProfile`.

- `python3 -m curvesim` will do a demo sim run so users can check everything is setup properly.

- Support use of environment variable (and loading from `.env` file) for
  `NOMICS_API_KEY`, `ALCHEMY_API_KEY`, and `ETHERSCAN_API_KEY`.  The latter two are optional
  in that the package provides default keys, but it is recommended to use your own if you need
  the functionality (currently only for pulling coin data for lending pools).
  
- Pipeline and iterators submodules added to support custom simulation pipelines.  This will allow
  more complex arbitrage scenarios and let users create bespoke simulations.

- Pool simulation interfaces added to decouple pool implementations from the simulation framework.
  The interfaces enable additional runtime optimizations.

- Standard volume-limited arbitrage simulation re-implemented using the new pipeline framework.

- Pools initiated from external data now store their metadata in pool.metadata for introspection
  and debugging.

- Create versioning structure to bump versions which will reflect in the
  changelog and future package releases.

- Added end-to-end tests for simulation runs that run in continuous integration.
  Unit tests added for pool calculations.  Increasing test coverage with component-level
  tests will be a key part of getting to v1.



Removed
-------

- sim() and psim() replaced by pipeline framework.

- PoolDF CSVs no longer used for pool data lookup.


Changed
-------

- Transitioned repo organization to reflect standard packaging style.

- Frequently used calculations such as `D`, `y`, and `dydxfee` use the GNU Multiple
  Precision Arithmetic Library (GMP) to speed up big integer arithmetic.

- The spot pricing function, `dydxfee`, uses a derivation from calculus instead of bumping
  a pool balance and recalculating, with the exception of a certain case for 
  metapools.

- The monolithic `Pool` class was split into a generic base class, with derived classes
  `CurvePool`, `CurveMetaPool`, and `CurveRaiPool`.

- Bonding curve and order-book `Pool` methods changed to standalone functions.

- "Price depth" metrics now report liquidity density (i.e., % change in holdings per 
  % change in price).

- Curvesim.autosim() now only accepts ints or iterables of ints for pool parameters
  (e.g., A, D, fee).
  
- External pool data now referenced using pool address or LP token symbol and chain.
  This logic is used in autosim and pool_data. 



Fixed
-----

- Subgraph volume query was updated due to a recent update.

- Fixed bug in vol_mode=2 for non-meta-pools

- Various updates to pool calculations to align the results with their on-chain equivalents.

- Codebase is much more PEP8 compliant with consistent style and formatting due to
  the enforced usage of tools such as `black`, `flake8`, and `pylint`.  This is particularly
  important as we onboard more contributors to the repo.
