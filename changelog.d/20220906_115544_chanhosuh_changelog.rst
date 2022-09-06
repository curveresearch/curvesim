Added
-----
- Single cpu-mode (`ncpu=1`) will run in a single process without the `multiprocessing`
  library.  This makes it easier to profile using tools like `cProfile`.
- `hello_world.py` test script so users can check everything is setup properly.

Changed
-------
- Frequently used calculations such as `D`, `y`, and `dydxfee` use the GNU Multiple
  Precision Arithmetic Library (GMP) to speed up big integer arithmetic.
- For regular pools, the `dydxfee` function uses a pricing derivation from calculus
  instead of bumping a pool balance and recalculating.

Fixed
-----
- Subgraph volume query was updated due to a recent update.

