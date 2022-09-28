__all__ = ["from_address", "from_symbol", "get", "queries"]
from curvesim.pool_data.queries import from_address, from_symbol


def get(address_or_symbol, chain="mainnet", src="cg", balanced=(True, True), days=60):
    if address_or_symbol.startswith("0x"):
        from_x = from_address
    else:
        from_x = from_symbol

    params = from_x(address_or_symbol, chain, balanced=balanced, days=days)
    return params
