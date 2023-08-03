from curvesim.exceptions import SimPoolError, CurvesimValueError
from curvesim.templates import SimAssets
from curvesim.templates.sim_pool import SimPool
from curvesim.utils import cache, override

from ..stableswap import CurvePool
from .asset_indices import AssetIndicesMixin


class SimCurvePool(SimPool, AssetIndicesMixin, CurvePool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.asset_names(self.coin_names.copy())

        rates = self.rates  # pylint: disable=no-member
        for r in rates:
            if r != 10**18:
                raise SimPoolError("SimPool must have 18 decimals for each coin.")

    @property
    @override
    @cache
    def asset_names(self):
        """Return list of asset names."""
        return self._asset_names

    @asset_names.setter
    @override
    def asset_names(self, *asset_names):
        """Set list of asset names."""
        if len(asset_names) != len(set(asset_names)):
            raise SimPoolError("SimPool must have unique asset names.")

        if hasattr(self, "asset_names") and len(self.asset_names) != len(asset_names):
            raise SimPoolError("SimPool must have a consistent number of asset names.")

        # edge case: user specifies an arbitrary number of existing asset names, but with 
        # at least one at a different index by mistake or as an attempt at switching coin indices
        
        self._asset_names = asset_names

    @property
    @override
    def _asset_balances(self):
        """Return list of asset balances in same order as asset_names."""
        return self.balances

    @override
    def price(self, coin_in, coin_out, use_fee=True):
        i, j = self.get_asset_indices(coin_in, coin_out)
        return self.dydx(i, j, use_fee=use_fee)

    @override
    def trade(self, coin_in, coin_out, size):
        """
        Note all quantities are in D units.
        """
        i, j = self.get_asset_indices(coin_in, coin_out)
        amount_out, fee = self.exchange(i, j, size)
        return amount_out, fee

    def get_in_amount(self, coin_in, coin_out, out_balance_perc):
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
