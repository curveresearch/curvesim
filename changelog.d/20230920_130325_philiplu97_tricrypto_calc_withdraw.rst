Added
-----

- Adapted CurveCryptoPool's _calc_withdraw_one_coin method to 3 coins.

Changed
-------
- In CurveCryptoPool, changed _tweak_price's param p_i to be Optional[int], where a 
  None value tells _tweak_price to calculate last prices from spot prices and a 0
  indicates an error in the calculation pipeline.

