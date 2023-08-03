"""Base SimPool implementation for Curve stableswap pools, both regular and meta."""
from abc import abstractmethod

from curvesim.exceptions import CurvesimValueError
from curvesim.utils import cache


class AssetIndicesMixin:
    """
    This mixin translates from asset names to Curve pool indices.
    Used in both stableswap and cryptoswap implementations used
    in arbitrage pipelines.
    """

    # we want to enforce valid inputs for asset_names and _asset_balances. 
        # both arrays are equal length
        # no duplicates in asset_names specifically
    
    # asset_names check:
        # -> SimPools automatically load metadata
        # -> add abstract asset_names.setter
        # -> AssetIndicesMixin children (SimPools) call their implementations in __init__ with a copy() of metadata
        # -> setter sets an attribute _asset_names to input array after passing checks

    # both arrays are equal length check:
        # in asset_balances below

    @property
    @abstractmethod
    def asset_names(self):
        """
        Return list of asset names.

        For metapools, our convention is to place the basepool LP token last.
        """
        raise NotImplementedError

    @asset_names.setter
    @abstractmethod
    def asset_names(self, *asset_lists):
        """
        Set list of asset names. 
        
        Implementations should disallow setting of duplicate names and inconsistent numbers of names.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def _asset_balances(self):
        """Return list of asset balances in same order as asset_names."""
        raise NotImplementedError

    @property
    def asset_balances(self):
        """Return dict mapping asset names to coin balances."""

        # check equal length 
        return dict(zip(self.asset_names, self._asset_balances))

    @property
    @cache
    def asset_indices(self):
        """
        Return dict mapping asset names to pool index.

        For metapools, our convention is to place the basepool LP token last, so that
        underlyer indices are preserved, but the basepool LP token is accessible using
        the index pool.n_total.
        """
        return {name: i for i, name in enumerate(self.asset_names)}

    def get_asset_indices(self, *asset_ids):
        """
        Gets the pool indices for the input asset names.
        Uses the indices set in _asset_indices.
        """
        indices = []
        for ID in asset_ids:
            if isinstance(ID, str):
                ID = self.asset_indices[ID]
            indices.append(ID)

        if len(indices) != len(set(indices)):
            raise CurvesimValueError("Duplicate asset indices.")

        return indices
