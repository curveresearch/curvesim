__all__ = [
    "StableSwapSimPool",
]

from curvesim.pool.stableswap.metapool import CurveMetaPool
from curvesim.pool.stableswap.pool import CurvePool
from curvesim.pool.stableswap.raipool import CurveRaiPool

from .. import functions as pool_functions
from . import metapool, pool
from .registry import register_interface
from .simpool import StableSwapSimPool

register_interface(CurvePool, pool, [pool_functions.dydx, pool_functions.dydx])

register_interface(
    CurveMetaPool,
    metapool,
    [pool_functions.dydx_metapool, pool_functions.dydx],
)

register_interface(
    CurveRaiPool,
    metapool,
    [pool_functions.dydx_metapool_rai, pool_functions.dydx_rai],
)
