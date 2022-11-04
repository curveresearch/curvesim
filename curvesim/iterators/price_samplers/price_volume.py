from ...price_data import get


class PriceVolume:
    """
    An iterator that retrieves price/volume and iterates over timepoints in the data.
    """

    def __init__(self, coins, days=60, data_dir="data", src="coingecko"):
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
            Identifies pricing source: coingecko, nomics, or local.

        """
        prices, volumes, pzero = get(coins, days=days, data_dir=data_dir, src=src)

        self.prices = prices
        self.volumes = volumes
        self.pzero = pzero

        self.price_generator = prices.iterrows()
        self.volume_generator = volumes.iterrows()

    def __iter__(self):
        return self

    def __next__(self):
        """
        Returns
        -------
        prices : pandas.Series
            Prices for each pairwise coin combination.

        volumes : pandas.Series
            Prices for each pairwise coin combination.

        timestamp : datetime.datetime
            Timestamp for the current price/volume.

        """
        prices = next(self.price_generator)
        volumes = next(self.volume_generator)

        assert prices[0] == volumes[0], "Price/volume timestamps did not match"

        return prices[1], volumes[1], prices[0]

    def total_volumes(self):
        """
        Returns
        -------
        pandas.Series
            Total volume for each pairwise coin combination, summed accross timestamps.
        """
        return self.volumes.sum()

    def restart(self):
        """
        Resets the iterator.

        Returns
        -------
        self
        """
        self.price_generator = self.prices.iterrows()
        self.volume_generator = self.volumes.iterrows()

        return self
