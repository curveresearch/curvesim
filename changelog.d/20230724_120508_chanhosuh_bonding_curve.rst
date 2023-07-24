Added
-----
- End-to-end test for the bonding curve that creates a pool
  using the `make` pool factory.  This covers some important
  gaps in our codebase.


Changed
-------
- Refactored the bonding curve function, separating the core logic
  from the plotting functionality.
- Created `tools` module to house the bonding curve and in anticipation
  of further tools, e.g. orderbook.
