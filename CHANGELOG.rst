
.. _changelog-0.2.0:

0.2.0 — 2022-11-08
==================

Removed
-------

-pool/data.py

Added
-----

- Single cpu-mode (`ncpu=1`) will run in a single process without the `multiprocessing`
  library.  This makes it easier to profile using tools like `cProfile`.
- `hello_world.py` test script so users can check everything is setup properly.

- Support use of environment variable (and loading from `.env` file) for
  `NOMICS_API_KEY`.
- Create versioning structure to bump versions which will reflect in the
  changelog and future package releases.

-multi-chain pool data support
-pool_data submodule
-network submodule

Changed
-------

- Frequently used calculations such as `D`, `y`, and `dydxfee` use the GNU Multiple
  Precision Arithmetic Library (GMP) to speed up big integer arithmetic.
- For regular pools, the `dydxfee` function uses a pricing derivation from calculus
  instead of bumping a pool balance and recalculating.

- Fixed bug in vol_mode=2 for non-meta-pools

- Transitioned repo organization to reflect standard packaging style.

Fixed
-----

- Subgraph volume query was updated due to a recent update.
