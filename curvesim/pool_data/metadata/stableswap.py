from curvesim.pool.stableswap.pool import CurvePool

from .base import PoolMetaDataBase
from ...logging import get_logger

logger = get_logger(__name__)


class StableswapMetaData(PoolMetaDataBase):
    """Specific implementation of the `PoolMetaDataInterface` for Stableswap."""

    def init_kwargs(self, normalize=True):
        data = self._dict
        logger.info(data)

        try:
            virtual_price = data["reserves"]["virtual_price"]  # subgraph format
        except:
            virtual_price = data["params"]["virtual_price"]  # curve prices format

        def process_to_kwargs(data, normalize):
            kwargs = {
                "A": data["params"]["A"],
                "n": len(data["coins"]["names"]),
                "fee": data["params"]["fee"],
                "fee_mul": data["params"]["fee_mul"],
                "admin_fee": data["params"]["admin_fee"],
                "virtual_price": virtual_price,
            }

            if normalize:
                coin_balances = data["reserves"]["by_coin"]
            else:
                coin_balances = data["reserves"]["unnormalized_by_coin"]

                if data["basepool"]:
                    d = data["coins"]["decimals"][0]
                    kwargs["rate_multiplier"] = 10 ** (36 - d)
                else:
                    kwargs["rates"] = [10 ** (36 - d) for d in data["coins"]["decimals"]]

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
            c = self._dict["coins"]["addresses"][:-1] + self._dict["basepool"]["coins"]["addresses"]
        return c

    @property
    def coin_names(self):
        if not self._dict["basepool"]:
            c = self._dict["coins"]["names"]
        else:
            c = self._dict["coins"]["names"][:-1] + self._dict["basepool"]["coins"]["names"]
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
