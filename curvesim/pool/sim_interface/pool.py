from curvesim.exceptions import SimPoolError
from curvesim.pipelines.templates import SimAssets
from curvesim.pipelines.templates.sim_pool import SimPool
from curvesim.utils import cache, override

from ..stableswap import CurvePool
from .coin_indices import CoinIndicesMixin


class SimCurvePool(SimPool, CoinIndicesMixin, CurvePool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        rates = self.rates  # pylint: disable=no-member
        for r in rates:
            if r != 10**18:
                raise SimPoolError("SimPool must have 18 decimals for each coin.")

    @property
    @override
    @cache
    def coin_indices(self):
        """Return dict mapping coin ID to index."""
        return {name: i for i, name in enumerate(self.coin_names)}

    @property
    @override
    def coin_balances(self):
        """Return dict mapping coin ID to coin balances."""
        return dict(zip(self.coin_names, self.balances))

    @override
    def price(self, coin_in, coin_out, use_fee=True):
        i, j = self.get_coin_indices(coin_in, coin_out)
        return self.dydx(i, j, use_fee=use_fee)

    @override
    def trade(self, coin_in, coin_out, amount_in):
        """
        Note all quantities are in D units.
        """
        i, j = self.get_coin_indices(coin_in, coin_out)
        amount_out, fee = self.exchange(i, j, amount_in)
        return amount_out, fee

    def get_in_amount(self, coin_in, coin_out, out_balance_perc):
        i, j = self.get_coin_indices(coin_in, coin_out)

        xp = self._xp()
        xp_j = int(xp[j] * out_balance_perc)

        in_amount = self.get_y(j, i, xp_j, xp) - xp[i]
        return in_amount

    @property
    @override
    @cache
    def assets(self):
        return SimAssets(self.coin_names, self.coin_addresses, self.chain)
