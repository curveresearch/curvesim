from hypothesis import given, settings
from hypothesis import strategies as st
from pandas import DataFrame

from itertools import product

from curvesim.pool.sim_interface import SimCurvePool, SimCurveRaiPool, SimCurveMetaPool

from curvesim.iterators.param_samplers import get_param_sampler, pool_param_sampler_map

# Template pools
meta_kwargs = {
    "A": 250,
    "D": 4000000 * 10**18,
    "n": 2,
    "admin_fee": 5 * 10**9,
    "basepool": SimCurvePool(A=250, D=1000000 * 10**18, n=2, admin_fee=5 * 10**9),
}
redemption_prices = DataFrame([1, 2, 3], columns=["price"])

sim_curve_pool = SimCurvePool(A=250, D=1000000 * 10**18, n=2, admin_fee=5 * 10**9)
sim_curve_meta_pool = SimCurveMetaPool(**meta_kwargs)
sim_curve_rai_pool = SimCurveRaiPool(**meta_kwargs, redemption_prices=redemption_prices)


# Strategies
def make_parameter_strats(*parameters):
    integer = st.integers(min_value=100, max_value=10000)

    parameter_strats = (
        make_dict_strat(parameters, integer, val_to_list=True),
        make_dict_strat(parameters, integer),
    )
    return parameter_strats


def make_dict_strat(keys, value_strat, val_to_list=False, min_size=1, max_size=None):
    """Generates list strategy from input strategy"""
    max_size = max_size or len(keys)
    key_strat = st.sampled_from(keys)

    if val_to_list:
        value_strat = to_list_strat(value_strat)

    return st.dictionaries(key_strat, value_strat, min_size=min_size, max_size=max_size)


def to_list_strat(strategy, min_size=2, max_size=20):
    """Generates list strategy from input strategy"""
    return st.lists(strategy, min_size=min_size, max_size=max_size, unique=True)


# Tests
def test_get_param_sampler():
    # TODO: add CryptoPool

    test_pools = [sim_curve_pool, sim_curve_meta_pool, sim_curve_rai_pool]
    test_args = [({"A": [10, 100, 1000]}, {"D": 10**26})] * 3  # stableswap args

    for sampler_type in pool_param_sampler_map:
        for pool, args in zip(test_pools, test_args):
            param_sampler = get_param_sampler(sampler_type, pool, *args)
            expected_class = pool_param_sampler_map[sampler_type][type(pool)]
            assert isinstance(param_sampler, expected_class)


@given(*make_parameter_strats("A", "D", "fee"))
@settings(max_examples=5, deadline=None)
def test_grid_curve_pool(variable_params, fixed_params):
    _test_grid(sim_curve_pool, variable_params, fixed_params)


@given(*make_parameter_strats("A", "D", "fee", "A_base", "D_base", "fee_base"))
@settings(max_examples=5, deadline=None)
def test_grid_curve_meta_pool(variable_params, fixed_params):
    _test_grid(sim_curve_meta_pool, variable_params, fixed_params)


@given(*make_parameter_strats("A", "D", "fee", "A_base", "D_base", "fee_base"))
@settings(max_examples=5, deadline=None)
def test_grid_curve_rai_pool(variable_params, fixed_params):
    _test_grid(sim_curve_rai_pool, variable_params, fixed_params)


# Test helper functions
def _test_grid(pool, variable_params, fixed_params):
    param_sampler = get_param_sampler("grid", pool, variable_params, fixed_params)
    assert pool != param_sampler.pool_template  # ensure deepcopy

    _test_pool_params(param_sampler.pool_template, fixed_params)
    _test_variable_params(param_sampler, variable_params)


def _test_pool_params(pool, params):
    for key, val in params.items():
        _pool, _key = parse_pool_attribute(pool, key)

        if _key == "D":
            assert abs(_pool.D() - val) < 15
        else:
            assert getattr(_pool, _key) == val


def _test_variable_params(param_sampler, variable_params):
    keys, values = zip(*variable_params.items())
    expected_sequence = []
    for vals in product(*values):
        params = dict(zip(keys, vals))
        expected_sequence.append(params)

    sequences = zip(param_sampler, param_sampler.parameter_sequence, expected_sequence)

    for (pool_sample, pool_params), sampler_params, expected_params in sequences:
        assert pool_params == sampler_params
        assert sampler_params == expected_params
        _test_pool_params(pool_sample, pool_params)


def parse_pool_attribute(pool, attribute):
    """
    Helper function to route "_base" attributes to basepool if necessary.
    """
    if attribute.endswith("_base"):
        return pool.basepool, attribute[:-5]

    return pool, attribute


# def test_grid
# -make_parameter_sequence
# -set_pool_attributes/_set_pool_attribute(
# -setters


# def test_
# CurvePoolMixin, CurveMetaPoolMixin, CurveCryptoPoolMixin
