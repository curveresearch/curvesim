from curvesim.pipelines.templates.sim_assets import SimAssets
from curvesim.pipelines.templates.sim_pool import SimPool


class CollateralizedDebtPosition(SimPool):
    def price(self, debt_token, collateral_token, use_fee=True):
        """
        Returns the effective price for collateral from liquidating
        the position.
        """

    def trade(self, debt_token, collateral_token, size):
        """
        Liquidate the position by paying `size` amount of the debt.
        """

    @property
    def number_of_coins(self):
        return 2

    @property
    def assets(self):
        # TODO: Use correct info
        symbols = None
        addresses = None
        chain = None
        return SimAssets(symbols, addresses, chain)

    def get_in_amount(self, coin_in, coin_out, out_balance_perc):
        """
        Might be something we use to calculate amount to repay?
        """
        raise Exception("This method is not used for the CDP pipeline.")
