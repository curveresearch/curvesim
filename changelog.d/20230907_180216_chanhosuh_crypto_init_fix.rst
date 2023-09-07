Added
-----

- `virtual_price` is an allowed optional argument for pools.

Fixed
-----

- Pool creation would fail if no `tokens` argument was provided to `CurveCryptoPool`.
- Wrong `D` value was computed for 3-coin `CurveCryptoPool`.
