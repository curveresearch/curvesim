class CurvePoolMixin:
    """
    Parameter sampler mixin for Curve stableswap pools.
    Defines special attribute setters.
    """

    @property
    def attribute_setters(self):
        return {"D": stableswap_D_to_balances}


class CurveMetaPoolMixin:
    """
    Parameter sampler mixin for Curve stableswap meta-pools.
    Defines special attribute setters.
    """

    @property
    def attribute_setters(self):
        return {"D": stableswap_D_to_balances}


class CurveCryptoPoolMixin:
    """
    Parameter sampler mixin for Curve cryptoswap pools.
    Defines special attribute setters.
    """

    @property
    def attribute_setters(self):
        return {}


def stableswap_D_to_balances(pool, D):
    rates = pool.rates[:]
    n = pool.n
    pool.balances = [D // n * 10**18 // p for p in rates]
