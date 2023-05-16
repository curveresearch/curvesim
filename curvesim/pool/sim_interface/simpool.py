"""Base SimPool implementation for Curve stableswap pools, both regular and meta."""
from abc import abstractmethod

from curvesim.exceptions import CurvesimValueError
from curvesim.pipelines.templates import SimPool
from curvesim.utils import cache


class SimStableswapBase(SimPool):
    """
    This base class contains common logic useful for all Curve
    stableswap implementations used in arbitrage pipelines:

    - translate from coin names to Curve pool indices
    - compute liquidity density of a coin pair and price-depth
    """

    @abstractmethod
    def _init_coin_indices(self):
        """Produces the coin ID to index mapping from the pool's metadata."""
        raise NotImplementedError

    @property
    @cache
    def coin_indices(self):
        """Return dict mapping coin ID to index."""
        return self._init_coin_indices()

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

    @abstractmethod
    def price(self, coin_in, coin_out, use_fee=True):
        raise NotImplementedError

    @abstractmethod
    def trade(self, coin_in, coin_out, size):
        raise NotImplementedError

    @abstractmethod
    def test_trade(self, coin_in, coin_out, factor):
        raise NotImplementedError

    @abstractmethod
    def make_error_fns(self):
        raise NotImplementedError
