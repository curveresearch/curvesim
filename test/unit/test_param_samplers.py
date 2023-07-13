import pytest

from hypothesis import given, settings
from hypothesis import strategies as st
from pandas import DataFrame

from itertools import product

from curvesim.exceptions import ParameterSamplerError
from curvesim.iterators.param_samplers import get_param_sampler, pool_param_sampler_map
from curvesim.pool.sim_interface import SimCurvePool, SimCurveRaiPool, SimCurveMetaPool


# Strategies
PARAM_STRATS = {
    "A": st.integers(min_value=10, max_value=3000),
    "D": st.integers(min_value=10**24, max_value=10**28),
    "fee": st.integers(min_value=10**10, max_value=10**11),
    "A_base": st.integers(min_value=10, max_value=3000),
    "D_base": st.integers(min_value=10**24, max_value=10**28),
    "fee_base": st.integers(min_value=10**10, max_value=10**11),
}


def make_parameter_strats(*parameters):
    """Returns param_subset_strats for variable_params and fixed_params arguments."""
    return (
        param_subset_strat(parameters, val_to_list=True),
        param_subset_strat(parameters, min_size=0),
    )


@st.composite
def param_subset_strat(draw, parameters, min_size=1, max_size=None, val_to_list=False):
    """
    Generates a dict including a subset of the provided parameters. This simulates
    user inputs to the parameter sampler (i.e., variable_params, fixed_params).

    Parameter values are taken from PARAM_STRATS. If val_to_list is True, generates a
    list of values for each parameter (i.e., in the format of variable_params).
    """
    max_size = max_size or len(parameters)

    key_strat = to_list_strat(
        st.sampled_from(parameters), min_size=min_size, max_size=max_size
    )

    keys = draw(key_strat)
    dict_subset = {}
    for key in keys:
        val_strat = PARAM_STRATS[key]
        if val_to_list:
            val_strat = to_list_strat(val_strat)
        dict_subset[key] = draw(val_strat)

    return dict_subset


def to_list_strat(strategy, min_size=2, max_size=20):
    """Makes list strategy from input strategy"""
    return st.lists(strategy, min_size=min_size, max_size=max_size, unique=True)


# Tests
def test_get_param_sampler():
    """Test class mapping and initializing using get_param_sampler()."""
    # TODO: add CryptoPool

    test_pools = POOLS.values()
    test_args = [({"A": [10, 100, 1000]}, {"D": 10**26})] * 3  # stableswap args

    for sampler_type in pool_param_sampler_map:
        for pool, args in zip(test_pools, test_args):
            param_sampler = get_param_sampler(sampler_type, pool, *args)
            expected_class = pool_param_sampler_map[sampler_type][type(pool)]
            assert isinstance(param_sampler, expected_class)


def test_param_sampler_exceptions():
    """Test exceptions for invalid parameter names."""
    pool = POOLS["sim_curve_pool"]

    # Not a pool param
    with pytest.raises(ParameterSamplerError):
        get_param_sampler("grid", pool, {"not_a_param": [20, 30]})

    # Basepool param when no basepool
    with pytest.raises(ParameterSamplerError):
        get_param_sampler("grid", pool, {"A_base": [10, 100]})


@given(*make_parameter_strats("A", "D", "fee"))
@settings(max_examples=5, deadline=None)
def test_grid_curve_pool(variable_params, fixed_params):
    _test_grid("sim_curve_pool", variable_params, fixed_params)


@given(*make_parameter_strats("A", "D", "fee", "A_base", "D_base", "fee_base"))
@settings(max_examples=5, deadline=None)
def test_grid_curve_meta_pool(variable_params, fixed_params):
    _test_grid("sim_curve_meta_pool", variable_params, fixed_params)


@given(*make_parameter_strats("A", "D", "fee", "A_base", "D_base", "fee_base"))
@settings(max_examples=5, deadline=None)
def test_grid_curve_rai_pool(variable_params, fixed_params):
    _test_grid("sim_curve_rai_pool", variable_params, fixed_params)


# TODO: add cryptopool


# Helper functions for tests
def _test_grid(pool_type, variable_params, fixed_params):
    pool = POOLS[pool_type]
    param_sampler = get_param_sampler("grid", pool, variable_params, fixed_params)
    assert pool != param_sampler.pool_template  # ensure deepcopy

    _test_pool_params(param_sampler.pool_template, fixed_params)
    _test_grid_variable_params(param_sampler, variable_params)


def _test_pool_params(pool, params):
    for key, val in params.items():
        _pool, _key = parse_pool_attribute(pool, key)

        if _key == "D":
            assert abs(_pool.D() - val) < 2
        else:
            assert getattr(_pool, _key) == val


def _test_grid_variable_params(param_sampler, variable_params):
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


# Pools
basepool = SimCurvePool(A=250, D=1000000 * 10**18, n=2, admin_fee=5 * 10**9)


def fixed_virtual_price():
    return 10**18


basepool.get_virtual_price = fixed_virtual_price

meta_kwargs = {
    "A": 250,
    "D": 4000000 * 10**18,
    "n": 2,
    "admin_fee": 5 * 10**9,
    "basepool": basepool,
}
rp = DataFrame([1, 2, 3], columns=["price"])

POOLS = {
    "sim_curve_pool": SimCurvePool(
        A=250, D=1000000 * 10**18, n=2, admin_fee=5 * 10**9
    ),
    "sim_curve_meta_pool": SimCurveMetaPool(**meta_kwargs),
    "sim_curve_rai_pool": SimCurveRaiPool(**meta_kwargs, redemption_prices=rp),
}
