__all__ = ["PoolMetaData", "PoolMetaDataInterface"]


from curvesim.exceptions import CurvesimException
from curvesim.network.subgraph import has_redemption_prices
from curvesim.pool.sim_interface import SimCurveMetaPool, SimCurvePool, SimCurveRaiPool
from curvesim.pool.stableswap import CurveMetaPool, CurvePool, CurveRaiPool

from .base import PoolMetaDataInterface
from .stableswap import StableswapMetaData

_SIM_POOL_TYPE = {
    CurvePool: SimCurvePool,
    CurveMetaPool: SimCurveMetaPool,
    CurveRaiPool: SimCurveRaiPool,
}

_METADATA_TYPE = {
    CurvePool: StableswapMetaData,
    CurveMetaPool: StableswapMetaData,
    CurveRaiPool: StableswapMetaData,
}


def PoolMetaData(metadata_dict):
    metadata_type, pool_type, sim_pool_type = _parse_metadata_for_types(metadata_dict)
    return metadata_type(metadata_dict, pool_type, sim_pool_type)


def _parse_metadata_for_types(metadata_dict):
    if metadata_dict["basepool"]:
        if _has_redemption_prices(metadata_dict):
            pool_type = CurveRaiPool
        else:
            pool_type = CurveMetaPool
    else:
        pool_type = CurvePool

    try:
        sim_pool_type = _SIM_POOL_TYPE[pool_type]
    except KeyError as e:
        raise CurvesimException(
            f"No sim pool type for this pool type: {pool_type}"
        ) from e
    try:
        metadata_type = _METADATA_TYPE[pool_type]
    except KeyError as e:
        raise CurvesimException(
            f"No metadata type for this pool type: {pool_type}"
        ) from e

    return metadata_type, pool_type, sim_pool_type


def _has_redemption_prices(metadata_dict):
    address = metadata_dict["address"]
    chain = metadata_dict["chain"]
    return has_redemption_prices(address, chain)
