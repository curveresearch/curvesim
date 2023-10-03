from curvesim.pool.stableswap.pool import CurvePool

from .base import PoolMetaDataBase


class StableswapMetaData(PoolMetaDataBase):
    """Specific implementation of the `PoolMetaDataInterface` for Stableswap."""

    def init_kwargs(self, normalize=True):
        data = self._dict

        def process_to_kwargs(data, normalize):
            kwargs = {
                "A": data["params"]["A"],
                "n": len(data["coins"]["names"]),
                "fee": data["params"]["fee"],
                "fee_mul": data["params"]["fee_mul"],
                "virtual_price": data["reserves"]["virtual_price"],
            }

            if normalize:
                coin_balances = data["reserves"]["normalized"]
            else:
                coin_balances = data["reserves"]["unnormalized"]

                if data["basepool"]:
                    d = data["coins"]["decimals"][0]
                    kwargs["rate_multiplier"] = 10 ** (36 - d)
                else:
                    kwargs["rates"] = [
                        10 ** (36 - d) for d in data["coins"]["decimals"]
                    ]

            kwargs["D"] = coin_balances

            return kwargs

        kwargs = process_to_kwargs(data, normalize)

        if data["basepool"]:
            bp_data = data["basepool"]
            bp_kwargs = process_to_kwargs(bp_data, normalize)
            basepool = CurvePool(**bp_kwargs)
            basepool.metadata = bp_data
            kwargs["basepool"] = basepool

        return kwargs

    @property
    def coins(self):
        if not self._dict["basepool"]:
            c = self._dict["coins"]["addresses"]
        else:
            c = (
                self._dict["coins"]["addresses"][:-1]
                + self._dict["basepool"]["coins"]["addresses"]
            )
        return c

    @property
    def coin_names(self):
        if not self._dict["basepool"]:
            c = self._dict["coins"]["names"]
        else:
            c = (
                self._dict["coins"]["names"][:-1]
                + self._dict["basepool"]["coins"]["names"]
            )
        return c

    @property
    def n(self):
        data = self._dict
        if data["basepool"]:
            n = [
                len(data["coins"]["names"]),
                len(data["basepool"]["coins"]["names"]),
            ]
        else:
            n = len(data["coins"]["names"])

        return n
