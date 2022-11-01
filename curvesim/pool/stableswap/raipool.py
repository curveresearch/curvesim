from .metapool import MetaPool


class RaiPool(MetaPool):
    def __init__(self, redemption_prices, *args, p=None, n=None, **kwargs):
        self.redemption_prices = redemption_prices

        p = p or [10**18] * n
        p[0] = int(redemption_prices.price[0])

        super().__init__(p=p, n=n, *args, **kwargs)

    def next_timestamp(self, timestamp, *args, **kwargs):
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
