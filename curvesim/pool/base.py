"""
Module housing the required implementation for any pool entity
in the Curvesim Framework.
"""


from curvesim.pool.snapshot import SnapshotMixin


class Pool(SnapshotMixin):
    """
    The `Pool` base class has the explicitly required properties for any
    pool-like object used in Curvesim.

    The `SnapshotMixin` gives the ability to snapshot balances and revert
    balance changes.

    Currently the base attributes are not informative for pools
    constructed manually rather than from chain data.
    """

    # need to configure in derived class otherwise the
    # snapshotting will not work
    snapshot_class = None

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
    def coin_names(self):
        """Symbols for the pool coins."""
        if hasattr(self, "metadata"):
            return self.metadata["coins"]["names"]
        return []

    @property
    def coin_addresses(self):
        """Addresses for the pool coins."""
        if hasattr(self, "metadata"):
            return self.metadata["coins"]["addresses"]
        return []

    @property
    def coin_decimals(self):
        """Addresses for the pool coins."""
        if hasattr(self, "metadata"):
            return self.metadata["coins"]["decimals"]
        return []

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

    @property
    def folder_name(self):
        """Name of folder containing saved sim results."""
        if hasattr(self, "metadata"):
            symbol = self.symbol
            address = self.address
            return symbol.lower() + "_" + address[:7].lower()
        return "custom_pool_" + str(hash(self))

    def __repr__(self):
        return f"<{self.__class__.__name__} address={self.address} chain={self.chain}>"
