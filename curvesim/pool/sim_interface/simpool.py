from abc import ABC, abstractmethod

from curvesim.exceptions import CurvesimValueError
from curvesim.pipelines.templates import SimPool


class SimStableswapBase(SimPool, ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._coin_indices = None

    @abstractmethod
    def _init_coin_indices(self):
        """Produces the coin ID to index mapping from the pool's metadata."""
        raise NotImplementedError

    @property
    def coin_indices(self):
        """Return dict mapping coin ID to index."""
        if self._coin_indices:
            indices = self._coin_indices
        else:
            indices = self._init_coin_indices()
            self._coin_indices = indices
        return indices

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

    def get_liquidity_density(self, coin_in, coin_out, factor=10**8):
        """
        Only for top-level liquidity density.  Cannot compare between
        coins in basepool and primary stablecoin in metapool.
        """
        price_pre = self.price(coin_in, coin_out)
        output = self._test_trade(coin_in, coin_out, factor)
        price_post = output[0]
        LD1 = price_pre / ((price_pre - price_post) * factor)

        price_pre = self.price(coin_out, coin_in)
        output = self._test_trade(coin_out, coin_in, factor)
        price_post = output[0]
        LD2 = price_pre / ((price_pre - price_post) * factor)

        return (LD1 + LD2) / 2

    def get_price_depth(self):
        LD = []
        for i, j in self._base_index_combos:
            ld = self.get_liquidity_density(i, j)
            LD.append(ld)
        return LD

    @property
    @abstractmethod
    def _base_index_combos(self):
        raise NotImplementedError

    @abstractmethod
    def _test_trade(self, coin_in, coin_out, dx):
        raise NotImplementedError
