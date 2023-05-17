from curvesim.pool.sim_interface import SimCurveMetaPool, SimCurvePool, SimCurveRaiPool


def get_pool_parameters(pool):
    return pool_parameter_functions[type(pool)](pool)


def get_curve_pool_params(pool):
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


def get_curve_metapool_params(pool):
    pool_params = get_curve_pool_params(pool)
    bp_params = get_curve_pool_params(pool.basepool)
    bp_params = {key + "_base": val for key, val in bp_params.items()}
    pool_params.update(bp_params)
    return pool_params


pool_parameter_functions = {
    SimCurvePool: get_curve_pool_params,
    SimCurveMetaPool: get_curve_metapool_params,
    SimCurveRaiPool: get_curve_metapool_params,
}
