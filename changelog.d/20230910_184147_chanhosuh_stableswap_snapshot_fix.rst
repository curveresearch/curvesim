Added
-----

- Each pool now has an internal method to handle conversion of the invariant
  to balances.  This is helpful for use by "friend" classes/functions such
  as factory functions.

Removed
-------

- The pool snapshot from subgraph is no longer being augmented with calculated
  data (see "Fixed" section for a related bug).  The snapshot functionality
  is solely limited to subgraph values with appropriate conversion into
  python types.

- Pool metadata no longer takes balancing options.  This is handled by the
  the appropriate factory function, namely `get_sim_pool`.

Fixed
-----

- Pool snapshot from subgraph was being augmented with some calculated values,
  namely `tokens` and `D`.  This value was incorrect for stableswap metapools.

  We have removed the augmented data and this is now being calculated as needed
  in the factory function `get_sim_pool`.  This is used to initialize the pool
  in a balanced state if desired.

  The calculation relies on the pool's internal logic, which we test rigorously
  in unit tests.

