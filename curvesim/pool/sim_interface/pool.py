from curvesim.utils import override

from ..stableswap import CurvePool
from .simpool import SimStableswapBase


class SimCurvePool(SimStableswapBase, CurvePool):
    @override
    def _init_coin_indices(self):
        return {name: i for i, name in enumerate(self.coin_names)}

    @override
    def price(self, coin_in, coin_out, use_fee=True):
        i, j = self.get_coin_indices(coin_in, coin_out)
        return self.dydx(i, j, use_fee=use_fee)

    @override
    def trade(self, coin_in, coin_out, size):
        """
        Note all quantities are in D units.
        """
        i, j = self.get_coin_indices(coin_in, coin_out)
        size = int(size)
        out_amount, fee = self.exchange(i, j, size)
        return out_amount, fee, size

    @override
    def test_trade(self, coin_in, coin_out, factor, use_fee=True):
        """
        This does the trade but leaves balances unaffected.

        Used to compute liquidity density.
        """
        i, j = self.get_coin_indices(coin_in, coin_out)

        size = self.balances[i] // factor

        with self.use_snapshot_context():
            self.exchange(i, j, size)
            price = self.dydx(i, j, use_fee=use_fee)

        return price

    def get_in_amount(self, coin_in, coin_out, out_balance_perc):
        i, j = self.get_coin_indices(coin_in, coin_out)

        xp = self._xp()
        xp_j = int(xp[j] * out_balance_perc)

        in_amount = self.get_y(j, i, xp_j, xp) - xp[i]
        return in_amount
