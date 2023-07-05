from curvesim.logging import get_logger
from curvesim.price_data import get
from curvesim.templates.samplers import PriceSample, PriceSampler
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

    @override
    def __iter__(self) -> PriceVolumeSample:
        """
        Yields
        -------
        class:`PriceVolumeSample`
        """
        for price_row, volume_row in zip(
            self.prices.iterrows(), self.volumes.iterrows()
        ):
            price_timestamp, prices = price_row
            volume_timestamp, volumes = volume_row
            assert (
                price_timestamp == volume_timestamp
            ), "Price/volume timestamps don't match"

            prices = prices.to_dict()
            volumes = volumes.to_dict()

            yield PriceVolumeSample(price_timestamp, prices, volumes)

    def total_volumes(self):
        """
        Returns
        -------
        pandas.Series
            Total volume for each pairwise coin combination, summed accross timestamps.
        """
        return self.volumes.sum().to_dict()
