from ...price_data import get


class PriceVolume:
    def __init__(self, coins, days=60, data_dir="data", src="coingecko"):
        prices, volumes, pzero = get(coins(), days=days, data_dir=data_dir, src=src)

        self.prices = prices
        self.volumes = volumes
        self.pzero = pzero

        self.price_generator = prices.iterrows()
        self.volume_generator = volumes.iterrows()

    def __iter__(self):
        return self

    def __next__(self):
        prices = next(self.price_generator)[1]
        volumes = next(self.volume_generator)[1]

        return prices, volumes

    def total_volumes(self):
        return self.volumes.sum()

    def restart(self):
        self.price_generator = self.prices.iterrows()
        self.volume_generator = self.volumes.iterrows()

        return self


class PriceVolumeRedemptionPrice:
    def __init__(
        self, coins, redemption_prices, days=60, data_dir="data", src="coingecko"
    ):

        prices, volumes, pzero = get(coins(), days=days, data_dir=data_dir, src=src)

        r = redemption_prices(t_start=prices.index[0])
        r = r.reindex(prices.index, method="ffill")

        self.prices = prices
        self.volumes = volumes
        self.pzero = pzero
        self.redemption_prices = r

        self.price_generator = prices.iterrows()
        self.volume_generator = volumes.iterrows()
        self.redemption_price_generator = r.iterrows()

    def __iter__(self):
        return self

    def __next__(self):
        prices = next(self.price_generator)[1]
        volumes = next(self.volume_generator)[1]
        redemption_price = next(self.redemption_price_generator)[1]

        return prices, volumes, redemption_price

    def total_volumes(self):
        return self.volumes.sum(axis=1)

    def reset(self):
        self.price_generator = self.prices.iterrows()
        self.volume_generator = self.volumes.iterrows()

        return self
