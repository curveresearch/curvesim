"""
Module housing the required implementation for any pool entity
in the Curvesim Framework.
"""


class Pool:
    """
    The `Pool` base class has the explicitly required properties for any pool-like
    object used in Curvesim.

    Currently the base attributes are not informative for pools
    constructed manually rather than from chain data.
    """

    @property
    def name(self):
        """Descriptive name for this pool"""
        if hasattr(self, "metadata"):
            return self.metadata["name"]
        return "Custom pool"

    @property
    def address(self):
        """Address on chain"""
        if hasattr(self, "metadata"):
            return self.metadata["address"]
        return "0x" + "0" * 40

    @property
    def chain(self):
        """Chain for this pool"""
        if hasattr(self, "metadata"):
            return self.metadata["chain"]
        return "No chain"

    @property
    def pool_type(self):
        """Type of this pool"""
        if hasattr(self, "metadata"):
            return self.metadata["pool_type"]
        return "Custom"

    @property
    def symbol(self):
        """LP token symbol"""
        if hasattr(self, "metadata"):
            return self.metadata["symbol"]
        return "Custom"

    def __repr__(self):
        return f"<{self.__class__.__name__} address={self.address} chain={self.chain}>"
