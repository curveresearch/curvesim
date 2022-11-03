from ...price_data import get


class PriceVolume:
    def __init__(self, coins, days=60, data_dir="data", src="coingecko"):
        """
        Parameters
        ----------
        coins: list of str
            addresses of coins in the pool
        days: int, defaults to 60
            number of last days to pull
        data_dir: str, defaults to "data"
            relative path to saved data folder
        src: str, defaults to "coingecko"
            identifies pricing source: coingecko, nomics, or local
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
        prices = next(self.price_generator)
        volumes = next(self.volume_generator)

        assert prices[0] == volumes[0], "Price/volume timestamps did not match"

        return prices[1], volumes[1], prices[0]

    def total_volumes(self):
        """
        Returns
        -------
        pandas.Series
            Total volume of all coins for each day.
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
