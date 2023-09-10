.. A new scriv changelog fragment.
..
.. Uncomment the header that is right (remove the leading dots).
..
.. Removed
.. -------
..
.. - A bullet item for the Removed category.
..
.. Added
.. -----
..
.. - A bullet item for the Added category.
..
.. Changed
.. -------
..
.. - A bullet item for the Changed category.
..
.. Deprecated
.. ----------
..
.. - A bullet item for the Deprecated category.
..
Fixed
-----

- Pool snapshot from subgraph was being augmented with some calculated values,
  namely `tokens` and `D`.  This value was incorrect for stableswap metapools.

  We have removed the augmented data and this is now being calculated as needed
  in the factory function `get_sim_pool`.  This is used to initialize the pool
  in a balanced state if desired.

  The calculation relies on the pool's internal logic, which we test rigorously
  in unit tests.

.. Security
.. --------
..
.. - A bullet item for the Security category.
..
