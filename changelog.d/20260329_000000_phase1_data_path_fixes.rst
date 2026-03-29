Changed
-------
- Updated Curve API usage to the current ``prices.curve.finance`` domain.
- Switched primary pool snapshot retrieval to the Curve API-backed ``curve_prices`` path.

Fixed
-----
- Fixed address-based pool metadata and ``autosim()`` failures caused by the deprecated hosted subgraph path.
- Restored ``autosim()`` compatibility for the documented ``days`` and ``test`` arguments.
- Fixed the CoinGecko ``matic`` chain alias mapping.
