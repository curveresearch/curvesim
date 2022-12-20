from curvesim.pool.stableswap.raipool import CurveRaiPool

from ..stableswap import functions as pool_functions
from .metapool import SimCurveMetaPool


class SimCurveRaiPool(CurveRaiPool, SimCurveMetaPool):
    @property
    def pricing_fns(self):
        return (pool_functions.dydx_metapool_rai, pool_functions.dydx_rai)
