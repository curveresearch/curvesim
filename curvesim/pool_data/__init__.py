__all__ = [
    "MetaPool",
    "Pool",
    "PoolData",
    "from_address",
    "from_symbol",
    "get",
    "queries",
]

from ..network.subgraph import redemption_prices_sync as _redemption_prices
from ..network.subgraph import volume_sync as _volume
from ..pool.metapool import MetaPool
from ..pool.pool import Pool
from .queries import from_address, from_symbol


def get(address_or_symbol, chain="mainnet", src="cg", balanced=(True, True), days=60):
    if address_or_symbol.startswith("0x"):
        from_x = from_address
    else:
        from_x = from_symbol

    params = from_x(address_or_symbol, chain, balanced=balanced)

    pool_data = PoolData(params)

    return pool_data


class PoolData(dict):
    def pool(self, balanced=(True, True)):
        def bal(kwargs, balanced):
            reserves = kwargs.pop("reserves")
            if not balanced:
                kwargs.update({"D": reserves})
            return kwargs

        kwargs = bal(self["init_kwargs"].copy(), balanced[0])

        if self["basepool"]:
            bp_kwargs = self["basepool"]["init_kwargs"].copy()
            bp_kwargs = bal(bp_kwargs, balanced[1])
            kwargs.update({"basepool": Pool(**bp_kwargs)})
            pool = MetaPool(**kwargs)
        else:
            pool = Pool(**kwargs)

        pool.metadata = self

        return pool

    def coins(self):
        if not self["basepool"]:
            c = self["coins"]["addresses"]
        else:
            c = self["coins"]["addresses"][:-1] + self["basepool"]["coins"]["addresses"]
        return c

    def volume(self, days=60):
        addrs = self["address"]
        chain = self["chain"]

        if self["basepool"]:
            addrs = [addrs, self["basepool"]["address"]]
            vol = _volume(addrs, chain, days=days)
            summed_vol = [sum(v) for v in vol]

        else:
            vol = _volume(addrs, chain, days=days)
            summed_vol = sum(vol)

        return summed_vol

    def redemption_prices(self, n=1000):
        address = self["address"]
        chain = self["chain"]

        r = _redemption_prices(address, chain, n=n)

        return r
