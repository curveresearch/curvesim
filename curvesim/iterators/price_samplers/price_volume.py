from dataclasses import dataclass
from datetime import datetime

from pandas import Series

from curvesim.price_data import get


class PriceVolume:
    """
    An iterator that retrieves price/volume and iterates over timepoints in the data.
    """

    def __init__(self, coins, days=60, data_dir="data", src="coingecko", end=None):
        """
        Retrieves price/volume data and prepares it for iteration.

        Parameters
        ----------
        coins: list of str
            Addresses of coins in the pool.

        days: int, defaults to 60
            Number of days to pull data for.

        data_dir: str, defaults to "data"
            Relative path to saved data folder.

        src: str, defaults to "coingecko"
            Identifies pricing source: coingecko or local.

        """
        prices, volumes, _ = get(coins, days=days, data_dir=data_dir, src=src, end=end)

        self.prices = prices
        self.volumes = volumes

    def __iter__(self):
        """
        Yields
        -------
        prices : pandas.Series
            Prices for each pairwise coin combination.

        volumes : pandas.Series
            Prices for each pairwise coin combination.

        timestamp : datetime.datetime
            Timestamp for the current price/volume.

        """
        for prices, volumes in zip(self.prices.iterrows(), self.volumes.iterrows()):
            assert prices[0] == volumes[0], "Price/volume timestamps did not match"
            yield PriceVolumeSample(prices[0], prices[1].values, volumes[1].values)

    def total_volumes(self):
        """
        Returns
        -------
        pandas.Series
            Total volume for each pairwise coin combination, summed accross timestamps.
        """
        return self.volumes.sum()


@dataclass(eq=False, slots=True)
class PriceVolumeSample:
    timestamp: datetime
    prices: Series
    volumes: Series
