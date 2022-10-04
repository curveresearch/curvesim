import asyncio

import numpy as np

from ..network.coingecko import crosschain_coin_addresses
from ..network.subgraph import redemption_price, snapshot, symbol_address
from ..network.web3 import underlying_coin_addresses


def from_address(address, chain, balanced=(True, True), days=60):
    loop = asyncio.get_event_loop()
    tasks = [snapshot(address, chain), redemption_price(address=address, chain=chain)]

    data, r = loop.run_until_complete(asyncio.gather(*tasks))

    # Add redemption price data
    data.update({"r": r})

    # Get mainnet addresses for coins
    addrs = data["coins"]["addresses"]
    m_addrs = loop.run_until_complete(
        crosschain_coin_addresses(addrs, chain, "mainnet")
    )
    data["coins"]["addresses"] = m_addrs

    # Get underlying token addresses
    if data["pool_type"] == "LENDING":
        u_addrs = loop.run_until_complete(underlying_coin_addresses(m_addrs))

        m = data.pop("coins")
        names = [n[1:] for n in m["names"]]

        data["coins"] = {"names": names, "addresses": u_addrs, "wrapper": m}

    pool_data = PoolData(data)

    return pool_data.legacy(balanced=balanced)


def from_symbol(symbol, chain, balanced=(True, True), days=60):
    loop = asyncio.get_event_loop()

    address = loop.run_until_complete(symbol_address(symbol, chain))

    pl_data = from_address(address, chain, balanced=balanced, days=days)

    return pl_data


class PoolData(dict):
    def pool(self, balanced=(True, True)):
        def bal(kwargs, balanced):
            reserves = kwargs.pop("reserves")
            if not balanced:
                kwargs.update({"D": reserves})
            return kwargs

        kwargs = bal(self["init_kwargs"].copy(), balanced[0])

        if self["basepool"]:
            bp_kwargs = bal(self["basepool"]["init_kwargs"], balanced[1])
            kwargs.update({"basepool": bp_kwargs})

        # to update: return pool object using kwargs
        # pool.metadata = self

        return kwargs

    def coins(self):
        if not self["basepool"]:
            c = self["coins"]["addresses"]
        else:
            c = self["coins"]["addresses"][:-1] + self["basepool"]["coins"]["addresses"]
        return c

    def volume(self):
        if not self["basepool"]:
            vol = np.array(self["volume"])
        else:
            vol = np.array([self["volume"], self["basepool"]["volume"]])
        return vol

    def redemption_prices(self):
        return self["r"]

    def legacy(self, balanced=(True, True)):
        pool = self.pool(balanced=balanced)

        if self["basepool"]:
            basepool = pool.pop("basepool")
            legacy_args = {
                "D": [pool["D"], basepool["D"]],
                "coins": self.coins(),
                "n": [pool["n"], basepool["n"]],
                "A": pool["A"],
                "A_base": basepool["A"],
                "fee": pool["fee"],
                "fee_base": basepool["fee"],
                "tokens": [pool["tokens"], basepool["tokens"]],
                "fee_mul": [pool["fee_mul"], basepool["fee_mul"]],
                "histvolume": self.volume(),
                "r": self.redemption_prices(),
            }
        else:
            legacy_args = {
                "D": pool["D"],
                "coins": self.coins(),
                "n": pool["n"],
                "A": pool["A"],
                "A_base": None,
                "fee": pool["fee"],
                "fee_base": None,
                "tokens": pool["tokens"],
                "fee_mul": pool["fee_mul"],
                "histvolume": self.volume(),
                "r": self.redemption_prices(),
            }

        return legacy_args
