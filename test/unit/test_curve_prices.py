from curvesim.network.curve_prices import _chain_from_alias


def test_curve_prices_chain_aliases():
    assert _chain_from_alias("mainnet") == "ethereum"
    assert _chain_from_alias("matic") == "polygon"
    assert _chain_from_alias("arbitrum") == "arbitrum"
