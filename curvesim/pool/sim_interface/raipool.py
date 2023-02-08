from curvesim.pool.stableswap.raipool import CurveRaiPool

from .metapool import SimCurveMetaPool


class SimCurveRaiPool(CurveRaiPool, SimCurveMetaPool):
    """Sim interface for Curve RAI metapool"""

    def __init__(self, redemption_prices, *args, **kwargs):
        """
        Parameters
        ----------
        redemption_prices : pandas.DataFrame
            timestamped redemption prices
            (see :meth:`.PoolData.redemption_prices()`)

        Other params as in `CurveRaiPool`.
        """
        self.redemption_prices = redemption_prices
        start_redemption_price = int(redemption_prices.price[0])
        super().__init__(*args, redemption_price=start_redemption_price, **kwargs)

    def prepare_for_trades(self, timestamp):
        """
        Updates the redemption price based on the input timestamp
        before computing and doing trades.

        Parameters
        ----------
        timestamp : datetime.datetime
            the time to sample from
        """
        r = self.redemption_prices.price.asof(timestamp)
        self.rate_multiplier = int(r)
