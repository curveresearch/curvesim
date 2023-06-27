"""Base SimPool implementation for Curve stableswap pools, both regular and meta."""
from abc import abstractmethod

from curvesim.exceptions import CurvesimValueError


class CoinIndicesMixin:
    """
    This mixin translates from coin names to Curve pool indices.
    Used in both stableswap and cryptoswap implementations used
    in arbitrage pipelines.
    """

    @property
    @abstractmethod
    def coin_indices(self):
        """Return dict mapping coin ID to index."""
        raise NotImplementedError

    def get_coin_indices(self, *coins_ids):
        """
        Gets the pool indices for the input coin names.
        Uses the coin_indices set by _init_coin_indices.
        """
        coin_indices = []
        for coin_id in coins_ids:
            if isinstance(coin_id, str):
                coin_id = self.coin_indices[coin_id]
            coin_indices.append(coin_id)

        if len(coin_indices) != len(set(coin_indices)):
            raise CurvesimValueError("Duplicate coin indices.")

        return coin_indices
