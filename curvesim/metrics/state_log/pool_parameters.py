"""
Getters for pool parameters of different pool types.

Used for the `StateLog`.
"""

from curvesim.exceptions import UnregisteredPoolError
from curvesim.pool.sim_interface import (
    SimCurveCryptoPool,
    SimCurveMetaPool,
    SimCurvePool,
    SimCurveRaiPool,
)


def get_pool_parameters(pool):
    """
    Returns pool parameters for the input pool. Functions for each pool type are
    specified in the `pool_parameter_functions` dict. Returned values are recorded
    at the start of each simulation run.
    """
    try:
        return pool_parameter_functions[type(pool)](pool)
    except KeyError as e:
        raise UnregisteredPoolError(
            f"Parameter getter not implemented for pool type '{type(pool)}'."
        ) from e


def get_cryptoswap_pool_params(pool):
    """Returns pool parameters for cryptoswap non-meta pools."""
    params = {
        "A": pool.A,
        "gamma": pool.gamma / 10**18,
        "D": pool.D / 10**18,
        "mid_fee": pool.mid_fee / 10**10,
        "out_fee": pool.out_fee / 10**10,
        "fee_gamma": pool.fee_gamma / 10**18,
        "allowed_extra_profit": pool.allowed_extra_profit / 10**18,
        "adjustment_step": pool.adjustment_step / 10**18,
        "ma_half_time": pool.ma_half_time,
    }

    for param_name in ["admin_fee"]:
        param_val = getattr(pool, param_name, None)
        if param_val:
            params.update({param_name: param_val / 10**10})

    return params


def get_stableswap_pool_params(pool):
    """Returns pool parameters for stableswap non-meta pools."""
    params = {
        "A": pool.A,
        "D": pool.D() / 10**18,
        "fee": pool.fee / 10**10,
    }

    for param_name in ["fee_mul", "admin_fee"]:
        param_val = getattr(pool, param_name, None)
        if param_val:
            params.update({param_name: param_val / 10**10})

    return params


def get_stableswap_metapool_params(pool):
    """Returns pool parameters for stableswap metapools."""
    pool_params = get_stableswap_pool_params(pool)
    bp_params = get_stableswap_pool_params(pool.basepool)
    bp_params = {key + "_base": val for key, val in bp_params.items()}
    pool_params.update(bp_params)
    return pool_params


pool_parameter_functions = {
    SimCurvePool: get_stableswap_pool_params,
    SimCurveMetaPool: get_stableswap_metapool_params,
    SimCurveRaiPool: get_stableswap_metapool_params,
    SimCurveCryptoPool: get_cryptoswap_pool_params,
}
