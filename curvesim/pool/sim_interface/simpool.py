"""Base SimPool implementation for Curve stableswap pools, both regular and meta."""
from abc import abstractmethod

from curvesim.exceptions import CurvesimValueError
from curvesim.pipelines.templates import SimPool
from curvesim.pool.snapshot import SnapshotMixin
from curvesim.utils import cache, override


class SimStableswapBase(SimPool, SnapshotMixin):
    """
    This base class contains common logic useful for all Curve
    stableswap implementations used in arbitrage pipelines:

    - translate from coin names to Curve pool indices
    - compute liquidity density of a coin pair and price-depth
    - ability to snapshot balances and revert balance changes
    """

    # need to configure in derived class otherwise the
    # snapshotting will not work
    snapshot_class = None

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

    def get_liquidity_density(self, coin_in, coin_out, factor=10**8):
        """
        Only for top-level liquidity density.  Cannot compare between
        coins in basepool and primary stablecoin in metapool.
        """
        price_pre = self.price(coin_in, coin_out, use_fee=False)
        price_post = self._test_trade(coin_in, coin_out, factor)
        LD1 = price_pre / ((price_pre - price_post) * factor)

        price_pre = self.price(coin_out, coin_in, use_fee=False)
        # pylint: disable-next=arguments-out-of-order
        price_post = self._test_trade(coin_out, coin_in, factor)
        LD2 = price_pre / ((price_pre - price_post) * factor)

        return (LD1 + LD2) / 2

    @override
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
    def _test_trade(self, coin_in, coin_out, factor):
        raise NotImplementedError
