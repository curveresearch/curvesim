from dataclasses import dataclass
from datetime import datetime

from pandas import Series

from curvesim.logging import get_logger
from curvesim.price_data import get

logger = get_logger(__name__)


class PriceVolume:
    """
    An iterator that retrieves price/volume and iterates over timepoints in the data.
    """

    def __init__(self, assets, days=60, data_dir="data", src="coingecko", end=None):
        """
        Retrieves price/volume data and prepares it for iteration.

        Parameters
        ----------
        assets: SimAssets
            Object giving the properties of the assets for simulation
            (e.g., symbols, addresses, chain)

        days: int, defaults to 60
            Number of days to pull data for.

        data_dir: str, defaults to "data"
            Relative path to saved data folder.

        src: str, defaults to "coingecko"
            Identifies pricing source: coingecko or local.

        """
        prices, volumes, _ = get(
            assets.addresses,
            chain=assets.chain,
            days=days,
            data_dir=data_dir,
            src=src,
            end=end,
        )

        self.prices = prices.set_axis(assets.symbol_pairs, axis="columns")
        self.volumes = volumes.set_axis(assets.symbol_pairs, axis="columns")

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
            yield PriceVolumeSample(
                prices[0], prices[1].to_dict(), volumes[1].to_dict()
            )

    def total_volumes(self):
        """
        Returns
        -------
        pandas.Series
            Total volume for each pairwise coin combination, summed accross timestamps.
        """
        return self.volumes.sum().to_dict()


@dataclass(eq=False, slots=True)
class PriceVolumeSample:
    timestamp: datetime
    prices: Series
    volumes: Series
