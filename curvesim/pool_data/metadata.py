from curvesim.exceptions import CurvesimException
from curvesim.network.subgraph import has_redemption_prices
from curvesim.pool.sim_interface import SimCurveMetaPool, SimCurvePool, SimCurveRaiPool
from curvesim.pool.stableswap import CurveMetaPool, CurvePool, CurveRaiPool


class PoolMetaData:

    _SIM_POOL_TYPE = {
        CurvePool: SimCurvePool,
        CurveMetaPool: SimCurveMetaPool,
        CurveRaiPool: SimCurveRaiPool,
    }

    def __init__(self, metadata_dict):
        self._dict = metadata_dict

    def init_kwargs(self, balanced=True, balanced_base=True):
        data = self._dict

        def process_to_kwargs(data, balanced):
            kwargs = {
                "A": data["params"]["A"],
                "D": data["reserves"]["D"],
                "n": len(data["coins"]["names"]),
                "fee": data["params"]["fee"],
                "fee_mul": data["params"]["fee_mul"],
                "tokens": data["reserves"]["tokens"],
            }
            if not balanced:
                kwargs["D"] = data["reserves"]["by_coin"]
            return kwargs

        kwargs = process_to_kwargs(data, balanced)

        if data["basepool"]:
            bp_data = data["basepool"]
            bp_kwargs = process_to_kwargs(bp_data, balanced_base)
            basepool = CurvePool(**bp_kwargs)
            basepool.metadata = bp_data
            kwargs["basepool"] = basepool

        return kwargs

    @property
    def address(self):
        return self._dict["address"]

    @property
    def chain(self):
        return self._dict["chain"]

    @property
    def has_redemption_prices(self):
        address = self.address
        chain = self.chain
        return has_redemption_prices(address, chain)

    @property
    def pool_type(self):
        if self._dict["basepool"]:
            if self.has_redemption_prices:
                _pool_type = CurveRaiPool
            else:
                _pool_type = CurveMetaPool
        else:
            _pool_type = CurvePool
        return _pool_type

    @property
    def sim_pool_type(self):
        pool_type = self.pool_type
        try:
            return self._SIM_POOL_TYPE[pool_type]
        except KeyError:
            raise CurvesimException(f"No sim pool type for this pool type: {pool_type}")

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
