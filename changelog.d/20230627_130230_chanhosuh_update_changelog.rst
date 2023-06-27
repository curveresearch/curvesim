The v0.4.5 milestone incoporated many cleanups and refactorings for improved readability and maintability in preparation for the cryptosim milestone.  We highlight the main ones below.


Added
-----
- Python 3.11 is now officially supported.
- Advanced custom metrics support (#117).
- CI now tests a matrix of OS and supported Python versions (#134)
- A simple pipeline was added to enable faster CI tests and serve as an easy example (#132).
- Integrated SimAssets into SimPools for simpler handling (#131).
- New classes Trade and TradeResult for better simulation results tracking.
- Support specifying end date when pulling data from Coingecko.
- Snapshot timestamp is now incorporated into metadata fetch (#133).


Improved
--------
- An updated README and the docs, especially for advanced metrics and strategies.
- Multiple changes to simplify and conform to simulation interfaces.
- Refactored SimStableswapBase into a mixin for better modularity (#146).
- ArbMetric updated for better numerical stability.
- Python-native types are now used in price_sampler, pool_data, pipeline (#137).
- Defensive check for sim pool precisions was added.


Fixed
-----
- Corrected layer 2 addresses in pool metadata (#130).


Removed
-------
- Unused Nomics wrapper and Coingecko code was removed.
- Old references to "freq" attribute from price sampler were removed (#118).

