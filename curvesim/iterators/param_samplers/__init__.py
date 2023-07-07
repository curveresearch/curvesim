"""
Iterators that generate pools with updated parameters for each simulation run.
"""

__all__ = [
    "Grid",
    "CurvePoolGrid",
    "CurveMetaPoolGrid",
    "CurveCryptoPoolGrid",
    "get_param_sampler",
]

from curvesim.pool.sim_interface import SimCurvePool, SimCurveRaiPool, SimCurveMetaPool
from .grid import Grid, CurvePoolGrid, CurveMetaPoolGrid, CurveCryptoPoolGrid


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
