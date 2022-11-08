from .metapool import CurveMetaPool


class CurveRaiPool(CurveMetaPool):
    """
    Rebasing stableswap metapool implementation in Python. Used for RAI3CRV pool.

    """

    def __init__(self, redemption_prices, *args, p=None, n=None, **kwargs):
        """
        Parameters
        ----------
        redemption_prices : pandas.DataFrame
            timestamped redemption prices
            (see :meth:`.PoolData.redemption_prices()`)
        A : int
            Amplification coefficient; this is :math:`A n^{n-1}` in the whitepaper.
        D : int or list of int
            coin balances or virtual total balance
        n: int
            number of coins
        p: list of int
            precision and rate adjustments
        tokens : int
            LP token supply
        fee : int, optional
            fee with 10**10 precision (default = .004%)
        fee_mul :
            fee multiplier for dynamic fee pools
        admin_fee : int, optional
            percentage of `fee` with 10**10 precision (default = 50%)
        """
        self.redemption_prices = redemption_prices

        p = p or [10**18] * n
        p[0] = int(redemption_prices.price[0])

        super().__init__(p=p, n=n, *args, **kwargs)

    def next_timestamp(self, timestamp, *args, **kwargs):
        """
        Updates the redemption price based on the input timestamp

        Parameters
        ----------
        timestamp : datetime.datetime
            the time to sample from

        """

        r = self.redemption_prices.price.asof(timestamp)
        self.p[0] = int(r)

    def dydx(self, i, j, dx=10**12, use_fee=False):
        _dydx = super().dydx(i, j, dx, use_fee=use_fee)

        if i >= self.max_coin and j < self.max_coin:
            base_i = i - self.max_coin
            _dydx = _dydx * self.basepool.p[base_i] / self.p[j]

        return _dydx

    def _dydx(self, i, j, xp, use_fee=False):
        dydx = super()._dydx(i, j, xp, use_fee=use_fee)
        return dydx * self.p[i] / self.p[j]
