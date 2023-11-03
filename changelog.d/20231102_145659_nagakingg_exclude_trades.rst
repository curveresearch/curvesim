Added
-----
- Added ArbTrade class to templates.trader. It is a Trade object with a 
  target price field, and a method to change the amount_in.

Changed
-------
- Changed arbitrage optimizers to exclude trades smaller than a 
  pool's minimum trade size from optimization. This reduces variability 
  in optimization and prevents some potential errors.

- Changed price errors returned by Traders to dicts indicating the
  trading pair for each error value.

- Changed price errors to be normalized by target price. 
