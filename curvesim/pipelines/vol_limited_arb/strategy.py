class VolumeLimitedStrategy(Strategy):

    arbitrageur_class = VolumeLimitedArbitrageur

    def __init__(self, metrics, vol_mult=None):
        super().__init__(metrics)
        self.vol_mult = vol_mult

    def _get_trader_inputs(self, sample):
        volume_limits = sample.volumes * self.vol_mult
        return sample.prices, volume_limits
