from curvesim.pool.sim_interface import SimCurvePool, SimCurveMetaPool


class CurvePoolMixin:
    """
    Parameter sampler mixin for Curve stableswap pools.
    Defines special attribute setters.
    """

    @property
    def _pool_type(self):
        return SimCurvePool

    @property
    def setters(self):
        return {"D": stableswap_D_to_balances}


class CurveMetaPoolMixin:
    """
    Parameter sampler mixin for Curve stableswap meta-pools.
    Defines special attribute setters.
    """

    @property
    def _pool_type(self):
        return SimCurveMetaPool

    @property
    def setters(self):
        return {"D": stableswap_D_to_balances, "D_base": stableswap_D_base_to_balances}


class CurveCryptoPoolMixin:
    """
    Parameter sampler mixin for Curve cryptoswap pools.
    Defines special attribute setters.
    """

    @property
    def _pool_type(self):
        raise NotImplementedError

    @property
    def setters(self):
        return {"D": cryptoswap_D_to_balances}


def stableswap_D_to_balances(pool, D):
    rates = pool.rates
    n = pool.n
    pool.balances = [D // n * 10**18 // r for r in rates]


def stableswap_D_base_to_balances(pool, D_base):
    basepool = pool.basepool
    rates = basepool.rates
    n = basepool.n
    basepool.balances = [D_base // n * 10**18 // r for r in rates]


def cryptoswap_D_to_balances(pool, D):
    n = pool.n
    price_scale = pool.price_scale
    precisions = pool.precisions

    if n == 2:
        price_scale = [price_scale]

    balances = [D // n // precisions[0]]
    divisors = zip(price_scale, precisions[1:])
    balances += [D * 10**18 // (n * price) // prec for price, prec in divisors]

    pool.balances = balances
