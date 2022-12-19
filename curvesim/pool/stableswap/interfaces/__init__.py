__all__ = [
    "StableSwapSimPool",
]

from curvesim.pool.stableswap.metapool import CurveMetaPool
from curvesim.pool.stableswap.pool import CurvePool
from curvesim.pool.stableswap.raipool import CurveRaiPool

from .. import functions as pool_functions
from .metapool import stableswap_metapool_fns
from .pool import stableswap_pool_fns
from .registry import register_interface
from .simpool import StableSwapSimPool

pricing_functions = (pool_functions.dydx, pool_functions.dydx)
register_interface(CurvePool, stableswap_pool_fns, pricing_functions)

pricing_functions = (pool_functions.dydx_metapool, pool_functions.dydx)
register_interface(CurveMetaPool, stableswap_metapool_fns, pricing_functions)

pricing_functions = (pool_functions.dydx_metapool_rai, pool_functions.dydx_rai)
register_interface(CurveRaiPool, stableswap_metapool_fns, pricing_functions)
