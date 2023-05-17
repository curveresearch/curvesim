from curvesim.pool.sim_interface import SimCurveMetaPool, SimCurvePool, SimCurveRaiPool


def get_pool_state(pool):
    return pool_state_functions[type(pool)](pool)


def get_curve_pool_state(pool):
    return {
        "balances": pool.balances,
        "tokens": pool.tokens,
        "admin_balances": pool.admin_balances,
    }


def get_curve_metapool_state(pool):
    state = get_curve_pool_state(pool)
    bp_state = get_curve_pool_state(pool.basepool)
    bp_state = {key + "_base": val for key, val in bp_state.items()}
    state.update(bp_state)
    return state


pool_state_functions = {
    SimCurvePool: get_curve_pool_state,
    SimCurveMetaPool: get_curve_metapool_state,
    SimCurveRaiPool: get_curve_metapool_state,
}
