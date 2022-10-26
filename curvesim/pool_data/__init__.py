__all__ = [
    "MetaPool",
    "Pool",
    "PoolData",
    "from_address",
    "from_symbol",
    "get",
    "queries",
]

from numpy import array

from ..network.subgraph import redemption_prices_sync as _redemption_prices
from ..network.subgraph import volume_sync as _volume
from ..pool.stableswap import MetaPool, Pool
from .queries import from_address, from_symbol


def get(address_or_symbol, chain="mainnet", src="cg", days=60):
    if address_or_symbol.startswith("0x"):
        from_x = from_address
    else:
        from_x = from_symbol

    params = from_x(address_or_symbol, chain)

    pool_data = PoolData(params)

    return pool_data


class PoolData:
    def __init__(self, metadata_dict, cache_data=False, days=60):
        self.dict = metadata_dict
        if cache_data:
            self.set_cache(days=days)

    def set_cache(self, days=60):
        self.volume(days=days, store=True)
        self.redemption_prices(store=True)

    def pool(self, balanced=(True, True)):
        def bal(kwargs, balanced):
            reserves = kwargs.pop("reserves")
            if not balanced:
                kwargs.update({"D": reserves})
            return kwargs

        kwargs = bal(self.dict["init_kwargs"].copy(), balanced[0])

        if self.dict["basepool"]:
            bp_kwargs = self.dict["basepool"]["init_kwargs"].copy()
            bp_kwargs = bal(bp_kwargs, balanced[1])
            kwargs.update({"basepool": Pool(**bp_kwargs)})
            pool = MetaPool(**kwargs)
        else:
            pool = Pool(**kwargs)

        pool.metadata = self.dict

        return pool

    def coins(self):
        if not self.dict["basepool"]:
            c = self.dict["coins"]["addresses"]
        else:
            c = (
                self.dict["coins"]["addresses"][:-1]
                + self.dict["basepool"]["coins"]["addresses"]
            )
        return c

    def volume(self, days=60, store=False, get_cache=True):
        if get_cache and hasattr(self, "_volume"):
            print("Getting cached historical volume...")
            return self._volume

        print("Fetching historical volume...")
        addrs = self.dict["address"]
        chain = self.dict["chain"]

        if self.dict["basepool"]:
            addrs = [addrs, self.dict["basepool"]["address"]]
            vol = _volume(addrs, chain, days=days)
            summed_vol = array([sum(v) for v in vol])

        else:
            vol = _volume(addrs, chain, days=days)
            summed_vol = array(sum(vol))

        if store:
            self._volume = summed_vol

        return summed_vol

    def n(self):
        if not self.dict["basepool"]:
            n = self.dict["init_kwargs"]["n"]
        else:
            n = [
                self.dict["init_kwargs"]["n"],
                self.dict["basepool"]["init_kwargs"]["n"],
            ]

        return n

    def type(self):
        if self.dict["basepool"]:
            return "MetaPool"
        else:
            return "Pool"

    def redemption_prices(self, n=1000, store=False, get_cache=True):
        if get_cache and hasattr(self, "_redemption_prices"):
            print("Getting cached redemption prices...")
            return self._redemption_prices

        print("Fetching redemption prices...")
        address = self.dict["address"]
        chain = self.dict["chain"]

        r = _redemption_prices(address, chain, n=n)

        if store:
            self._redemption_prices = r

        return r
