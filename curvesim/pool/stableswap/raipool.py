from .metapool import CurveMetaPool


class CurveRaiPool(CurveMetaPool):
    """
    Rebasing stableswap metapool implementation in Python. Used for RAI3CRV pool.

    """

    def __init__(self, redemption_price, *args, **kwargs):
        """
        Parameters
        ----------
        redemption_price : int
            redemption price for the pool; functionally equivalent to `rate_multiplier`
            for a factory metapool
        A : int
            Amplification coefficient; this is :math:`A n^{n-1}` in the whitepaper.
        D : int or list of int
            coin balances or virtual total balance
        n: int
            number of coins
        tokens : int
            LP token supply
        fee : int, optional
            fee with 10**10 precision (default = .004%)
        fee_mul :
            fee multiplier for dynamic fee pools
        admin_fee : int, optional
            percentage of `fee` with 10**10 precision (default = 50%)
        """
        super().__init__(*args, rate_multiplier=redemption_price, **kwargs)

    def dydx(self, i, j, use_fee=False):
        _dydx = super().dydx(i, j, use_fee=use_fee)

        if i >= self.max_coin and j == 0:
            base_i = i - self.max_coin
            _dydx = _dydx * self.basepool.rates[base_i] / self.rate_multiplier

        return _dydx

    def _dydx(self, i, j, xp, use_fee=False):
        dydx = super()._dydx(i, j, xp, use_fee=use_fee)
        rates = self.rates
        return dydx * rates[i] / rates[j]
