
.. _changelog-0.3.0:

0.3.0 — 2022-11-08
==================


Added
-----

- multi-chain pool data support via the Convex Community subgraph
- network submodule uses `asyncio` for concurrency
- pool_data submodule

- Single cpu-mode (`ncpu=1`) will run in a single process without the `multiprocessing`
  library.  This makes it easier to profile using tools like `cProfile`.

- `python3 -m curvesim` will do a demo sim run so users can check everything is setup properly.

- Support use of environment variable (and loading from `.env` file) for
  `NOMICS_API_KEY`.

- Create versioning structure to bump versions which will reflect in the
  changelog and future package releases.



Removed
-------

- pool/data.py
- 


Changed
-------

- Transitioned repo organization to reflect standard packaging style.

- Frequently used calculations such as `D`, `y`, and `dydxfee` use the GNU Multiple
  Precision Arithmetic Library (GMP) to speed up big integer arithmetic.

- For regular pools, the `dydxfee` function uses a pricing derivation from calculus
  instead of bumping a pool balance and recalculating.

- Fixed bug in vol_mode=2 for non-meta-pools

- Pool class was split into two classes, `CurvePool` and `CurveMetaPool`.



Fixed
-----

- Subgraph volume query was updated due to a recent update.
