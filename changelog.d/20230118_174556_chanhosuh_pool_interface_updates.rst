
Added
-----

- Curve pool types now use `__slots__` for more performant attribute access.
- Revamped pool hierarchy so that the implementations of `SimPool` derive
  from Curve pools and `SimStableSwapBase`, which better organizes common
  logic across stableswap sim pool types and decouples sim logic from the
  core AMM pools.
- Sim pools now have a revert-to-snapshot functionality.

Changed
-------

- `CurveMetaPool` uses `rate_multiplier` as in the vyper logic instead of `p`
- Upgraded `titanoboa` dependency to 0.1.6

Fixed
-----

- Use `rates` property consistently across stableswap types
- Add error handling for convex subgraph


Removed
-------

- Standalone functions for AMM logic are removed.  This eases the testing burden
  without impacting performance (due to other changes such as `__slot__` usage).
