from curvesim.exceptions import SimPoolError
from curvesim.templates.sim_pool import SimPool
from curvesim.utils import cache, override

from ..stableswap import CurvePool
from .asset_indices import AssetIndicesMixin


class SimCurvePool(SimPool, AssetIndicesMixin, CurvePool):
    """
    Class to enable use of CurvePool in simulations by exposing
    a generic interface (`SimPool`).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        rates = self.rates  # pylint: disable=no-member
        for r in rates:
            if r != 10**18:
                raise SimPoolError("SimPool must have 18 decimals for each coin.")

    @property
    @override
    @cache
    def asset_names(self):
        """Return list of asset names."""
        return self.coin_names

    @property
    @override
    def _asset_balances(self):
        """Return list of asset balances in same order as asset_names."""
        return self.balances

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
        return self.dydx(i, j, use_fee=use_fee)

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
        amount_out, fee = self.exchange(i, j, size)
        return amount_out, fee

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

        xp = self._xp()
        xp_j = int(xp[j] * out_balance_perc)

        in_amount = self.get_y(j, i, xp_j, xp) - xp[i]
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
