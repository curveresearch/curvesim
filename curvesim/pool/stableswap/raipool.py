from .metapool import CurveMetaPool


class CurveRaiPool(CurveMetaPool):
    """
    Rebasing stableswap metapool implementation in Python. Used for RAI3CRV pool.

    """

    def __init__(self, redemption_prices, *args, **kwargs):
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
        rate_multiplier: int
            precision and rate adjustment for primary stable in metapool
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
        rate_multiplier = int(redemption_prices.price[0])

        super().__init__(*args, rate_multiplier=rate_multiplier, **kwargs)

    def next_timestamp(self, timestamp, *args, **kwargs):
        """
        Updates the redemption price based on the input timestamp

        Parameters
        ----------
        timestamp : datetime.datetime
            the time to sample from

        """

        r = self.redemption_prices.price.asof(timestamp)
        self.rate_multiplier = int(r)

    def dydx(self, i, j, use_fee=False):
        _dydx = super().dydx(i, j, use_fee=use_fee)

        if i >= self.max_coin and j == 0:
            base_i = i - self.max_coin
            _dydx = _dydx * self.basepool.p[base_i] / self.rate_multiplier

        return _dydx

    def _dydx(self, i, j, xp, use_fee=False):
        dydx = super()._dydx(i, j, xp, use_fee=use_fee)
        rates = self.rates
        return dydx * rates[i] / rates[j]
