from curvesim.pipelines.arbitrage import DEFAULT_PARAMS, volume_limited_arbitrage
from curvesim.pool_data import get as get_pool_data


def autosim(pool=None, chain="mainnet", pool_data=None, **kwargs):
    assert any([pool, pool_data]), "Must input 'pool' or 'pool_data'"

    pool_data = pool_data or get_pool_data(pool, chain)
    p_var, p_fixed, kwargs = parse_arguments(**kwargs)

    results = volume_limited_arbitrage(
        pool_data, variable_params=p_var, fixed_params=p_fixed, **kwargs
    )

    return results


def parse_arguments(**kwargs):
    pool_args = ["A", "D", "x", "p", "fee", "fee_mul", "tokens", "admin_fee"]
    basepool_args = [arg + "_base" for arg in pool_args[:-1]]

    variable_params = {}
    fixed_params = {}
    rest_of_params = {}
    defaults = DEFAULT_PARAMS.copy()

    for key, val in kwargs.items():
        if key in defaults:
            del defaults[key]

        if key in pool_args:
            if isinstance(val, int):
                fixed_params.update({key: val})

            elif all([isinstance(v, int) for v in val]):
                variable_params.update({key: val})

            else:
                raise TypeError(f"Argument {key} must be an int or iterable of ints")

        elif key in basepool_args:
            if isinstance(val, int):
                fixed_params.setdefault("basepool", {})
                fixed_params["basepool"].update({key[:-5]: val})

            elif all([isinstance(v, int) for v in val]):
                variable_params.setdefault("basepool", {})
                variable_params["basepool"].update({key[:-5]: val})

            else:
                raise TypeError(f"Argument {key} must be an int or iterable of ints")
        else:
            rest_of_params[key] = val

    variable_params = variable_params or defaults

    return variable_params, fixed_params, rest_of_params
