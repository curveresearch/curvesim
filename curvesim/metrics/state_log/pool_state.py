from curvesim.exceptions import UnregisteredPoolError
from curvesim.pool.sim_interface import (
    SimCurveCryptoPool,
    SimCurveMetaPool,
    SimCurvePool,
    SimCurveRaiPool,
)


def get_pool_state(pool):
    """
    Returns pool state for the input pool. Functions for each pool type are
    specified in the `pool_state_functions` dict. Each function returns the
    values necessary to reconstruct pool state throughout a simulation run.
    """
    try:
        return pool_state_functions[type(pool)](pool)
    except KeyError as e:
        raise UnregisteredPoolError(
            f"State getter not implemented for pool type '{type(pool)}'."
        ) from e


def get_cryptoswap_pool_state(pool):
    """Returns pool state for stableswap non-meta pools."""
    return {
        "D": pool.D,
        "balances": pool.balances,
        "tokens": pool.tokens,
        "price_scale": pool.price_scale,
        "_price_oracle": pool._price_oracle,  # pylint: disable=protected-access
        "xcp_profit": pool.xcp_profit,
        "xcp_profit_a": pool.xcp_profit_a,
        "last_prices": pool.last_prices,
        "last_prices_timestamp": pool.last_prices_timestamp,
        "not_adjusted": pool.not_adjusted,
    }


def get_stableswap_pool_state(pool):
    """Returns pool state for stableswap non-meta pools."""
    return {
        "balances": pool.balances,
        "tokens": pool.tokens,
        "admin_balances": pool.admin_balances,
    }


def get_stableswap_metapool_state(pool):
    """Returns pool state for stableswap non-meta pools."""
    state = get_stableswap_pool_state(pool)
    bp_state = get_stableswap_pool_state(pool.basepool)
    bp_state = {key + "_base": val for key, val in bp_state.items()}
    state.update(bp_state)
    return state


pool_state_functions = {
    SimCurvePool: get_stableswap_pool_state,
    SimCurveMetaPool: get_stableswap_metapool_state,
    SimCurveRaiPool: get_stableswap_metapool_state,
    SimCurveCryptoPool: get_cryptoswap_pool_state,
}
