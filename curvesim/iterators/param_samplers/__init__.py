"""
Iterators that generate pools with updated parameters per simulation run.
"""

from curvesim.pool.sim_interface import SimCurvePool, SimCurveRaiPool, SimCurveMetaPool
from .grid import CurvePoolGrid, CurveMetaPoolGrid


pool_param_sampler_map = {
    "grid": {
        SimCurvePool: CurvePoolGrid,
        SimCurveRaiPool: CurveMetaPoolGrid,
        SimCurveMetaPool: CurveMetaPoolGrid,
        # SimCurveCryptoPool: CurveCryptoPoolGrid
    },
}


def get_param_sampler(sampler_type, pool, *args, **kwargs):
    sampler_class = pool_param_sampler_map[sampler_type][type(pool)]
    return sampler_class(pool, *args, **kwargs)
