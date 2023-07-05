from curvesim.exceptions import CurvesimValueError, SimPoolError
from curvesim.templates import SimAssets
from curvesim.templates.sim_pool import SimPool
from curvesim.utils import cache, override

from ..cryptoswap import CurveCryptoPool
from .asset_indices import AssetIndicesMixin


class SimCurveCryptoPool(SimPool, AssetIndicesMixin, CurveCryptoPool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for p in self.precisions:
            if p != 0:
                raise SimPoolError("SimPool must have 18 decimals for each coin.")

    @property
    @override
    @cache
    def coin_indices(self):
        """Return dict mapping coin ID to index."""
        coin_dict = {name: i for i, name in enumerate(self.coin_names)}
        return coin_dict

    @override
    def price(self, coin_in, coin_out, use_fee=True):
        i, j = self.get_asset_indices(coin_in, coin_out)

        if i == j:
            raise CurvesimValueError("Duplicate coin indices.")

        xp = self._xp()
        # return self._dydx(i, j, xp=xp, use_fee=use_fee)
        raise NotImplementedError("Need to implement!")

    @override
    def trade(self, coin_in, coin_out, amount_in):
        """
        Trade between two coins in a pool.
        Coins run over basepool underlyers.

        Note all quantities are in D units.
        """
        i, j = self.get_asset_indices(coin_in, coin_out)
        amount_out, fee = self.exchange(i, j, amount_in)
        return amount_out, fee

    def get_in_amount(self, coin_in, coin_out, out_balance_perc):
        i, j = self.get_asset_indices(coin_in, coin_out)
        raise NotImplementedError("Need to implement!")

    @property
    @override
    @cache
    def assets(self):
        symbols = None
        addresses = None
        chain = self.chain

        return SimAssets(symbols, addresses, chain)
