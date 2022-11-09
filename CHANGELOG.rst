
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
  `NOMICS_API_KEY`.
  
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
