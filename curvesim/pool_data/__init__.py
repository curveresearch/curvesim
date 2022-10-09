__all__ = ["from_address", "from_symbol", "get", "queries"]
from curvesim.pool_data.queries import from_address, from_symbol


def get(address_or_symbol, chain="mainnet", src="cg", balanced=(True, True), days=60):
    if address_or_symbol.startswith("0x"):
        from_x = from_address
    else:
        from_x = from_symbol

    params = from_x(address_or_symbol, chain, balanced=balanced, days=days)

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
            vol = self["volume"]
        else:
            vol = [self["volume"], self["basepool"]["volume"]]
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
