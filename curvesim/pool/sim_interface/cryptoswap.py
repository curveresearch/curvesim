"""Module to house the `SimPool` extension of the `CurveCryptoPool`."""
from curvesim.exceptions import SimPoolError
from curvesim.templates import SimAssets
from curvesim.templates.sim_pool import SimPool
from curvesim.utils import cache, override

from ..cryptoswap import CurveCryptoPool
from .asset_indices import AssetIndicesMixin


class SimCurveCryptoPool(SimPool, AssetIndicesMixin, CurveCryptoPool):
    """
    Class to enable use of CurveCryptoPool in simulations by exposing
    a generic interface (`SimPool`).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        precisions = self.precisions  # pylint: disable=no-member
        for p in precisions:
            if p != 1:
                raise SimPoolError(
                    "SimPool must have 18 decimals (precision 1) for each coin."
                )

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
        # need to implement a dydxfee equivalent on the cryptopool
        raise SimPoolError("`price` not implemented for SimCurveCryptoPool.")

    @override
    def trade(self, coin_in, coin_out, size):
        """
        Perform an exchange between two coins.

        Coin IDs should be strings but as a legacy feature integer indices
        corresponding to the pool implementation are allowed (caveat lector).

        Note that all amounts are normalized to be in the same units as
        pool value, i.e. `XCP`.  This simplifies cross-token comparisons
        and creation of metrics.


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

    def get_in_amount(self, coin_in, coin_out, out_balance_perc):
        """
        Get the approximate in-amount to achieve the given percentage
        of the out-token balance.

        Parameters
        ----------
        coin_in: int
            name or index of in-token
        coin_out: int
            name or index of out-token
        out_balance_perc : float
            percentage of the out-token balance that should remain after swap

        Returns
        -------
        int
            An approximate quantity to swap to achieve the target out-token
            balance
        """
        i, j = self.get_asset_indices(coin_in, coin_out)

        xp = self._xp()
        xp_j = int(xp[j] * out_balance_perc)

        in_amount = self.get_y(j, i, xp_j, xp) - xp[i]
        return in_amount

    @property
    @override
    @cache
    def assets(self):
        return SimAssets(self.coin_names, self.coin_addresses, self.chain)
