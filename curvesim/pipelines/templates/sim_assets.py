from curvesim.utils import get_pairs


class SimAssets:
    """
    Stores the properties of the assets to be used in a simulation. Currently, only
    specific coins identified by their address/chain are supported. This will be
    expanded to "abstract" assets (e.g., some function of multiple coins) in the near
    future.
    """

    def __init__(self, symbols, addresses, chain):
        self.symbols = symbols
        self.addresses = addresses
        self.chain = chain
        self.symbol_pairs = get_pairs(symbols)
        self.address_pairs = get_pairs(addresses)
