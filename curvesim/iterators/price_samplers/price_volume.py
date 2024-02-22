"""
Contains PriceVolume price sampler and PriceVolumeSample dataclass.
"""

from typing import Iterator

from pandas import DataFrame

from curvesim.logging import get_logger
from curvesim.templates.price_samplers import PriceSample, PriceSampler
from curvesim.utils import dataclass, override

logger = get_logger(__name__)


@dataclass(slots=True)
class PriceVolumeSample(PriceSample):
    """
    Attributes
    -----------
    timestamp : datetime.datetime
        Timestamp for the current price/volume.
    prices : dict
        Price for each pairwise coin combination.
    volumes : dict
        Volume for each pairwise coin combination.
    """

    volumes: dict


class PriceVolume(PriceSampler):
    """
    Iterates over price and volume data in the provided DataFrame.
    """

    def __init__(self, data: DataFrame):
        """
        Parameters
        ----------
        data: DataFrame
            DataFrame with prices and volumes for each asset pair.

            Format should match output of :fun:"curvesim.price_data.get_price_data".
            Row indices: datetime.datetime or pandas.Timestamp.
            Column indices: MultIndex with "price" and "volume" level 1 for each tuple
            of symbols in level 2.
        """
        self.data = data

    @override
    def __iter__(self) -> Iterator[PriceVolumeSample]:
        """
        Yields
        -------
        :class:`PriceVolumeSample`
        """
        for row in self.data.iterrows():
            timestamp, row_data = row

            prices = row_data["price"].to_dict()
            volumes = row_data["volume"].to_dict()

            yield PriceVolumeSample(timestamp, prices, volumes)  # type:ignore

    @property
    def prices(self):
        """
        Returns price data for all asset pairs.

        Returns
        -------
        pandas.DataFrame
        """
        return self.data["price"]

    @property
    def volumes(self):
        """
        Returns volume data for all asset pairs.

        Returns
        -------
        pandas.DataFrame
        """
        return self.data["volume"]
