from curvesim.pool.sim_interface import SimCurveMetaPool, SimCurvePool, SimCurveRaiPool


def get_pool_state(pool):
    """
    Returns pool state for the input pool. Functions for each pool type are
    specified in the `pool_state_functions` dict.
    """
    return pool_state_functions[type(pool)](pool)


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
}
