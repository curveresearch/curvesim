"""
Various network connectors and related utilities.

Primary data sources for general exchange prices and volumes are Coingecko and Nomics.
Curve subgraph is used for fetching pool data.  The Llama Airforce REST API will also
be used in the future.

There is not a well-defined public API for this subpackage yet.  A lot of the code
has been converted to use `asyncio` from a legacy implementation and further,
substantive improvements are anticipated.
"""
