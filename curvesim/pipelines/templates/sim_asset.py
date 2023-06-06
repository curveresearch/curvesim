class SimAsset:
    """
    Stores the properties of an asset to be used in a simulation. Currently, only
    specific coins identified by their address/chain are supported. This will be
    expanded to "abstract" assets (e.g., some function of multiple coins) in the near
    future.
    """

    def __init__(self, symbol, address, chain):
        self.symbol = symbol
        self.address = address
        self.chain = chain
