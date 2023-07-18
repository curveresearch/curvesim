from curvesim.exceptions import SimPoolError
from curvesim.templates import SimAssets
from curvesim.templates.sim_pool import SimPool
from curvesim.utils import cache, override

from ..cryptoswap import CurveCryptoPool
from .asset_indices import AssetIndicesMixin


class SimCurveCryptoPool(SimPool, AssetIndicesMixin, CurveCryptoPool):
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
        # TODO: fill this method in
        raise SimPoolError("Price not implemented for SimCurveCryptoPool.")

    @override
    def trade(self, coin_in, coin_out, amount_in):
        """
        Note all quantities are in D units.
        """
        i, j = self.get_asset_indices(coin_in, coin_out)
        amount_out, fee = self.exchange(i, j, amount_in)
        return amount_out, fee

    def get_in_amount(self, coin_in, coin_out, out_balance_perc):
        i, j = self.get_asset_indices(coin_in, coin_out)

        A = self.A
        gamma = self.gamma
        xp = self._xp()
        D = self._newton_D(A, gamma, xp)

        xp[j] = int(xp[j] * out_balance_perc)
        in_amount = self._newton_y(A, gamma, xp, D, j)
        return in_amount

    @property
    @override
    @cache
    def assets(self):
        return SimAssets(self.coin_names, self.coin_addresses, self.chain)
