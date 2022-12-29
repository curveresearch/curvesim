from curvesim.pool.stableswap.raipool import CurveRaiPool

from .metapool import SimCurveMetaPool


class SimCurveRaiPool(CurveRaiPool, SimCurveMetaPool):
    """Sim interface for Curve RAI metapool"""
