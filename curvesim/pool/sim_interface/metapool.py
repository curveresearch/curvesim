from curvesim.exceptions import CurvesimValueError, SimPoolError
from curvesim.templates.sim_pool import SimPool
from curvesim.utils import cache, override

from ..stableswap import CurveMetaPool
from .asset_indices import AssetIndicesMixin


class SimCurveMetaPool(SimPool, AssetIndicesMixin, CurveMetaPool):
    """
    Class to enable use of CurveMetaPool in simulations by exposing
    a generic interface (`SimPool`).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # The rates check has a couple special cases:
        # 1. For metapools, we need to use the basepool rates
        #    instead of the virtual price for the basepool.
        # 2. If `rate_multiplier` is passed as a kwarg, this will
        #    likely be some price, which we should skip.
        rates = [self.rate_multiplier] + self.basepool.rates
        if "rate_multiplier" in kwargs:
            rates = rates[1:]

        for r in rates:
            if r != 10**18:
                raise SimPoolError("SimPool must have 18 decimals for each coin.")

    @property
    @override
    @cache
    def asset_names(self):
        """
        Return list of asset names.

        For metapools, our convention is to place the basepool LP token last.
        """
        meta_coin_names = self.coin_names[:-1]
        base_coin_names = self.basepool.coin_names
        bp_token_name = self.coin_names[-1]

        return [*meta_coin_names, *base_coin_names, bp_token_name]

    @property
    @override
    def _asset_balances(self):
        """Return list of asset balances in same order as asset_names."""
        meta_balances = self.balances[:-1]
        base_balances = self.basepool.balances
        bp_token_balances = self.balances[-1]

        return [*meta_balances, *base_balances, bp_token_balances]

    @override
    def price(self, coin_in, coin_out, use_fee=True):
        """
        Returns the spot price of `coin_in` quoted in terms of `coin_out`,
        i.e. the ratio of output coin amount to input coin amount for
        an "infinitesimally" small trade.

        Coin IDs should be strings but as a legacy feature integer indices
        corresponding to the pool implementation are allowed (caveat lector).

        The indices are assumed to include base pool underlyer indices.

        Parameters
        ----------
        coin_in : str, int
            ID of coin to be priced; in a swapping context, this is
            the "in"-token.
        coin_out : str, int
            ID of quote currency; in a swapping context, this is the
            "out"-token.
        use_fee: bool, default=True
            Deduct fees.

        Returns
        -------
        float
            Price of `coin_in` quoted in `coin_out`
        """
        i, j = self.get_asset_indices(coin_in, coin_out)
        bp_token_index = self.n_total

        if bp_token_index not in (i, j):
            return self.dydx(i, j, use_fee=use_fee)

        i, j = self.get_meta_asset_indices(i, j, bp_token_index)
        xp = self._xp()
        return self._dydx(i, j, xp=xp, use_fee=use_fee)

    @override
    def trade(self, coin_in, coin_out, size):
        """
        Perform an exchange between two coins.

        Coin IDs should be strings but as a legacy feature integer indices
        corresponding to the pool implementation are allowed (caveat lector).

        Note that all amounts are normalized to be in the same units as
        pool value, e.g. for Curve Stableswap pools, the same units as `D`.
        This simplifies cross-token comparisons and creation of metrics.


        Parameters
        ----------
        coin_in : str, int
            ID of "in" coin.
        coin_out : str, int
            ID of "out" coin.
        size : int
            Amount of coin `i` being exchanged.

        Returns
        -------
        (int, int)
            (amount of coin `j` received, trading fee)
        """
        i, j = self.get_asset_indices(coin_in, coin_out)
        bp_token_index = self.n_total

        if bp_token_index not in (i, j):
            return self.exchange_underlying(i, j, size)

        i, j = self.get_meta_asset_indices(i, j, bp_token_index)
        return self.exchange(i, j, size)

    def get_meta_asset_indices(self, i, j, bp_token_index):
        """
        Get metapool asset indices from the output of get_coin_indices.
        """
        max_coin = self.max_coin

        if i == bp_token_index:
            i = max_coin

        if j == bp_token_index:
            j = max_coin

        if i == j:
            raise CurvesimValueError("Duplicate coin indices.")

        if i > max_coin or j > max_coin:
            raise CurvesimValueError(
                f"Index exceeds max metapool index (Input: {(i,j)}, Max: {max_coin})."
            )

        return i, j

    @override
    def get_max_trade_size(self, coin_in, coin_out, out_balance_perc=0.01):
        """
        Calculate the swap amount of the "in" coin needed to leave
        the specified percentage of the "out" coin.

        Parameters
        ----------
        coin_in : str, int
            ID of "in" coin.
        coin_out : str, int
            ID of "out" coin.
        out_balance_perc : float
            Percentage of the "out" coin balance that should remain
            after doing the swap.

        Returns
        -------
        int
            The amount of "in" coin needed.
        """
        i, j = self.get_asset_indices(coin_in, coin_out)

        max_coin = self.max_coin

        xp_meta = self._xp_mem(self.balances, self.rates)
        xp_base = self._xp_mem(self.basepool.balances, self.basepool.rates)

        base_i = i - max_coin
        base_j = j - max_coin
        meta_i = max_coin
        meta_j = max_coin
        if base_i < 0:
            meta_i = i
        if base_j < 0:
            meta_j = j

        if base_i < 0 or base_j < 0:
            xp_j = int(xp_meta[meta_j] * out_balance_perc)
            in_amount = self.get_y(meta_j, meta_i, xp_j, xp_meta)
            in_amount -= xp_meta[meta_i]
        else:
            xp_j = int(xp_base[base_j] * out_balance_perc)
            in_amount = self.basepool.get_y(base_j, base_i, xp_j, xp_base)
            in_amount -= xp_base[base_i]

        return in_amount

    @override
    def get_min_trade_size(self, coin_in):
        """
        Return the minimal trade size allowed for the pool.

        Parameters
        ----------
        coin_in : str, int
            ID of "in" coin.

        Returns
        -------
        int
            The minimal trade size
        """
        return 0
