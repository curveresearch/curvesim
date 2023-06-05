"""Base SimPool implementation for Curve stableswap pools, both regular and meta."""
from abc import abstractmethod

from curvesim.exceptions import CurvesimValueError, SimPoolError
from curvesim.pipelines.templates import SimPool
from curvesim.utils import cache, override


class SimStableswapBase(SimPool):
    """
    This base class contains common logic useful for all Curve
    stableswap implementations used in arbitrage pipelines:

    - translate from coin names to Curve pool indices
    - compute liquidity density of a coin pair and price-depth
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # The rates check has a couple special cases:
        # 1. For metapools, we need to use the basepool rates
        #    instead of the virtual price for the basepool.
        # 2. If `rate_multiplier` is passed as a kwarg, this will
        #    likely be some price, which we should skip.
        if hasattr(self, "rate_multiplier"):
            rates = [self.rate_multiplier] + self.basepool.rates
        else:
            rates = self.rates  # pylint: disable=no-member

        if "rate_multiplier" in kwargs:
            rates = rates[1:]

        for r in rates:
            if r != 10**18:
                raise SimPoolError("SimPool must have 18 decimals for each coin.")

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

    @property
    @override
    def number_of_coins(self):
        return self.n_total  # pylint: disable=no-member

    @abstractmethod
    def get_in_amount(self, coin_in, coin_out, out_balance_perc):
        raise NotImplementedError
