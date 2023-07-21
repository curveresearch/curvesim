Added
------

- The focus of this update was to update the CurveCryptoPool class to handle 3 coins for the functionality
  required for cryptoswap simulations, namely `exchange`, `_tweak_price`, and the related calculations.  The pythonic
  equivalents such as `add_liquidity`, `remove_liquidity_one_coin`, etc., were not updated.
  For the supported calculations, the pool will give exact integer results as compared to the Tricrypto-NG contract.
