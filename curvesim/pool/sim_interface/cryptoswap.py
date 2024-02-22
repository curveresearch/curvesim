"""Module to house the `SimPool` extension of the `CurveCryptoPool`."""
from math import prod

from curvesim.exceptions import SimPoolError
from curvesim.templates.sim_pool import SimPool
from curvesim.utils import cache, override

from ..cryptoswap import CurveCryptoPool
from ..cryptoswap.calcs import newton_D
from ..cryptoswap.calcs.factory_2_coin import _sqrt_int
from ..cryptoswap.calcs.tricrypto_ng import _cbrt
from .asset_indices import AssetIndicesMixin


# pylint: disable-next=too-many-instance-attributes
class SimCurveCryptoPool(SimPool, AssetIndicesMixin, CurveCryptoPool):
    """
    Class to enable use of CurveCryptoPool in simulations by exposing
    a generic interface (`SimPool`).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        precisions = self.precisions  # pylint: disable=no-member
        for p in precisions:
            if p != 1:
                raise SimPoolError(
                    "SimPool must have 18 decimals (precision 1) for each coin."
                )

    @property
    @override
    @cache
    def asset_names(self):
        """Return list of asset names."""
        return self.coin_names

    @property
    @override
    def _asset_balances(self):
        """Return list of asset balances in same order as asset_names."""
        return self.balances

    @override
    def price(self, coin_in, coin_out, use_fee=True):
        """
        Returns the spot price of `coin_in` quoted in terms of `coin_out`,
        i.e. the ratio of output coin amount to input coin amount for
        an "infinitesimally" small trade.

        Coin IDs should be strings but as a legacy feature integer indices
        corresponding to the pool implementation are allowed (caveat lector).

        Parameters
        ----------
        coin_in : str, int
            ID of coin to be priced; in a swapping context, this is
            the "in"-token.
        coin_out : str, int
            ID of quote currency; in a swapping context, this is the
            "out"-token.
        use_fee: bool, default=True
            Deduct fees.

        Returns
        -------
        float
            Price of `coin_in` quoted in `coin_out`
        """
        i, j = self.get_asset_indices(coin_in, coin_out)
        p = self.dydx(i, j, use_fee=use_fee)
        return p

    @override
    def trade(self, coin_in, coin_out, size):
        """
        Perform an exchange between two coins.

        Coin IDs should be strings but as a legacy feature integer indices
        corresponding to the pool implementation are allowed (caveat lector).

        Note that all amounts are normalized to be in the same units as
        pool value, i.e. `XCP`.  This simplifies cross-token comparisons
        and creation of metrics.


        Parameters
        ----------
        coin_in : str, int
            ID of "in" coin.
        coin_out : str, int
            ID of "out" coin.
        size : int
            Amount of coin `i` being exchanged.

        Returns
        -------
        (int, int)
            (amount of coin `j` received, trading fee)
        """
        i, j = self.get_asset_indices(coin_in, coin_out)
        amount_out, fee = self.exchange(i, j, size)
        return amount_out, fee

    @override
    def get_max_trade_size(self, coin_in, coin_out, out_balance_perc=0.15):
        """
        Get the approximate in-amount to achieve the given percentage
        of the out-token balance.

        Parameters
        ----------
        coin_in: int
            name or index of in-token
        coin_out: int
            name or index of out-token
        out_balance_perc : float
            percentage of the out-token balance that should remain after swap

        Returns
        -------
        int
            An approximate quantity to swap to achieve the target out-token
            balance
        """
        i, j = self.get_asset_indices(coin_in, coin_out)

        xp = self._xp()
        xp_j = int(xp[j] * out_balance_perc)

        in_amount = self.get_y(j, i, xp_j, xp) - xp[i]
        if i > 0:
            in_amount = in_amount * 10**18 // self.price_scale[i - 1]
        return in_amount

    @override
    def get_min_trade_size(self, coin_in):
        """
        Return the minimal trade size allowed for the pool.

        Parameters
        ----------
        coin_in : str, int
            ID of "in" coin.

        Returns
        -------
        int
            The minimal trade size
        """
        (i,) = self.get_asset_indices(coin_in)
        min_amount = 10**18
        if i > 0:
            min_amount = min_amount * 10**18 // self.price_scale[i - 1]
        return min_amount

    @override
    def prepare_for_trades(self, timestamp):
        """
        Updates the pool's _block_timestamp attribute to current sim time.

        Parameters
        ----------
        timestamp : datetime.datetime
            The current timestamp in the simulation.
        """

        timestamp = int(timestamp.timestamp())  # unix timestamp in seconds
        self._increment_timestamp(timestamp=timestamp)

    @override
    def prepare_for_run(self, prices):
        """
        Sets price parameters to the first simulation price and updates
        balances to be equally-valued.

        Balances are updated so that xcp(D) is preserved, but D may change.

        Parameters
        ----------
        timestamp : pandas.DataFrame
            The price time_series, price_sampler.prices.
        """
        xcp = self._get_xcp(self.D)
        n = self.n

        if n == 2:
            root = _sqrt_int
        elif n == 3:
            root = _cbrt

        # Get/set initial prices
        initial_prices = prices.iloc[0, 0 : n - 1].tolist()
        initial_prices = [int(10**18 / p) for p in initial_prices]

        self.last_prices = initial_prices.copy()
        self.price_scale = initial_prices.copy()
        self._price_oracle = initial_prices.copy()

        # Upbdate balances, preserving xcp
        initial_prices_root = [root(p) for p in initial_prices]
        new_D = prod(initial_prices_root) * xcp * n // 10 ** (18 * (n - 1))
        self.balances = self._convert_D_to_balances(new_D)

        # Recompute D with new balances
        xp = self._xp()
        self.D = newton_D(self.A, self.gamma, xp)

        # Set virtual price & xcp profit to 1
        self.tokens = self._get_xcp(self.D)
        self.virtual_price = self.get_virtual_price()
        self.xcp_profit = 10**18
        self.xcp_profit_a = 10**18
