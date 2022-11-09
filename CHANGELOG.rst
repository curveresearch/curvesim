
.. _changelog-0.3.0:

0.3.0 — 2022-11-08
==================


Added
-----

- Multi-chain pool data support via the Convex Community subgraph.

- Network submodule uses `asyncio` for concurrency.

- Pool_data and price_data submodules added.

- Single cpu-mode (`ncpu=1`) will run in a single process without the `multiprocessing`
  library.  This makes it easier to profile using tools like `cProfile`.

- `python3 -m curvesim` will do a demo sim run so users can check everything is setup properly.

- Support use of environment variable (and loading from `.env` file) for
  `NOMICS_API_KEY`.
  
- Pipeline and iterators submodules added to support custom simulation pipelines.

- Pool simulation interfaces added for additional simulation optimization.

- Standard volume-limited arbitrage simulation re-implemented using the new pipeline framework.

- Pools initiated from external data now store their metadata in pool.metadata.

- Create versioning structure to bump versions which will reflect in the
  changelog and future package releases.



Removed
-------

- pool/data.py

- Sim() and psim() replaced by pipeline framework.

- PoolDF CSVs no longer needed for pool data lookup.


Changed
-------

- Transitioned repo organization to reflect standard packaging style.

- Frequently used calculations such as `D`, `y`, and `dydxfee` use the GNU Multiple
  Precision Arithmetic Library (GMP) to speed up big integer arithmetic.

- For regular pools, the `dydxfee` function uses a pricing derivation from calculus
  instead of bumping a pool balance and recalculating.

- Pool class was split into two classes, `CurvePool` and `CurveMetaPool`.

- `CurveRaiPool` was added as a subclass of `CurveMetaPool`.

- Bonding curve and order-book methods changed to standalone functions.

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
