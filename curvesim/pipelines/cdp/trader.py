from numpy import array
from scipy.optimize import root_scalar

from curvesim.logging import get_logger
from curvesim.pipelines.templates.trader import Trade, Trader

logger = get_logger(__name__)


class Liquidator(Trader):
    """
    Computes, executes, and reports out arbitrage trades.
    """

    def compute_trades(self, prices):
        """
        Compute trades to arbitrage the pool, as follows:
            1. For each coin pair i and j, calculate size of coin i
               needed to move price of coin i w.r.t. to j to the
               target price.
            2. Calculate the profit from each such swap.
            3. Take the swap that gives the largest profit.

        Parameters
        ----------
        prices : pandas.Series
            Current market prices from the price_sampler.

        Returns
        -------
        trades: List[Tuple]
            List of trades to perform.

            Each trade is a tuple (coin_in, coin_out, size).

            "coin_in": in token
            "coin_out": out token
            "size": trade size

        price_errors: numpy.ndarray
            Post-trade price error between pool price and market price.
        """
        cdp = self.pool

        trade = None
        price_error = None
        # TODO: liquidation logic
        if cdp.price(debt, collateral) < prices[(debt, collateral)]:
            size = cdp.get_amount_in()

        if not trade:
            return [], {"price_errors": array([])}

        return [trade], {"price_errors": array([price_error])}
