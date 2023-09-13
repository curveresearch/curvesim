from math import prod

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from curvesim.exceptions import ParameterSamplerError
from curvesim.iterators.param_samplers import ParameterizedPoolIterator
from curvesim.iterators.param_samplers.parameterized_pool_iterator import (
    DEFAULT_POOL_MAP,
)
from curvesim.pool.cryptoswap.calcs import newton_D
from curvesim.pool.sim_interface import SimCurveCryptoPool

# Strategies
POOL_PARAMS = {
    "A": st.integers(min_value=1, max_value=3000),
    "D": st.integers(min_value=10**24, max_value=10**28),
    "fee": st.integers(min_value=10**10, max_value=10**11),
}

METAPOOL_PARAMS = {
    "A": st.integers(min_value=1, max_value=3000),
    "D": st.integers(min_value=10**24, max_value=10**28),
    "fee": st.integers(min_value=10**10, max_value=10**11),
    "A_base": st.integers(min_value=10, max_value=3000),
    "D_base": st.integers(min_value=10**24, max_value=10**28),
    "fee_base": st.integers(min_value=10**10, max_value=10**11),
}

CRYPTOPOOL_PARAMS = {
    "D": st.integers(min_value=10**24, max_value=10**28),
    "A": st.integers(min_value=4000, max_value=4000000000),
    "gamma": st.integers(min_value=10**10, max_value=2 * 10**16),
    "mid_fee": st.integers(min_value=5 * 10**5, max_value=10**10),
    "out_fee": st.integers(min_value=5 * 10**5, max_value=10**10),
    "allowed_extra_profit": st.integers(min_value=0, max_value=10**8),
    "fee_gamma": st.integers(min_value=0, max_value=10**10),
    "adjustment_step": st.integers(min_value=0, max_value=10**10),
    "ma_half_time": st.integers(min_value=0, max_value=604800),
}


def make_parameter_strats(parameters):
    """
    Returns param_subset_strats for variable_params and fixed_params arguments.

    Note: variable params are limited to length 1 and fixed params limited to length 0.
    Variable params of length 0 are tested seperately in
    test_ParameterizedPoolIterator_no_variable_params.
    """
    return (
        param_subset_strat(parameters, val_to_list=True),
        param_subset_strat(parameters, min_size=0),
    )


@st.composite
def param_subset_strat(draw, parameters, min_size=1, max_size=None, val_to_list=False):
    """
    Generates a dict including a subset of the provided parameters. This simulates
    user inputs to the parameter sampler (i.e., variable_params, fixed_params).

    Parameter values are taken from param_strats. If val_to_list is True, generates a
    list of values for each parameter (i.e., in the format of variable_params).
    """
    max_size = max_size or len(parameters)

    key_strat = to_list_strat(
        st.sampled_from(list(parameters)), min_size=min_size, max_size=max_size
    )

    key_subset = draw(key_strat)
    dict_subset = {}
    for key in key_subset:
        val_strat = parameters[key]
        if val_to_list:
            val_strat = to_list_strat(val_strat, max_size=3)
        dict_subset[key] = draw(val_strat)

    return dict_subset


def to_list_strat(strategy, min_size=2, max_size=20):
    """Makes list strategy from input strategy"""
    return st.lists(strategy, min_size=min_size, max_size=max_size, unique=True)


# Tests
def test_invalid_parameter_exceptions(sim_curve_pool):
    """
    Test exceptions for invalid parameter names. If fails,
    ParameterSampler._validate_attributes is malfunctioning.
    """

    # Not a pool param
    with pytest.raises(ParameterSamplerError):
        ParameterizedPoolIterator(sim_curve_pool, {"not_a_param": [20, 30]})

    # Basepool param when no basepool
    with pytest.raises(ParameterSamplerError):
        ParameterizedPoolIterator(sim_curve_pool, {"A_base": [10, 100]})


def test_ParameterizedPoolIterator_subclass_mapping():
    """
    Test ParameterizedPoolIterator subclass mapping and instantiation.
    If fails, __new__ or subclass instantiation is failing.
    """

    class DummyPool:
        def __init__(self):
            for attr in "abcd":
                setattr(self, attr, None)

    class DummyParamSampler(ParameterizedPoolIterator):
        @property
        def _pool_type(self):
            return DummyPool

    mapping = {DummyPool: DummyParamSampler}
    pool = DummyPool()
    variable_params = {"a": [1, 2], "b": [3, 4]}
    fixed_params = {"c": 5, "d": 6}

    param_sampler = ParameterizedPoolIterator(
        pool, variable_params, fixed_params, pool_map=mapping
    )

    assert isinstance(param_sampler, DummyParamSampler)
    assert isinstance(param_sampler.pool_template, DummyPool)


def test_ParameterizedPoolIterator_unmapped_pool_exception():
    """
    Test ParameterizedPoolIterator exception for unmapped pool type.
    If fails, ParameterizedPoolIterator.__new__ is failing.
    """

    class DummyPool:
        def __init__(self):
            for attr in "ab":
                setattr(self, attr, None)

    pool = DummyPool()

    with pytest.raises(ParameterSamplerError):
        ParameterizedPoolIterator(pool)


def test_ParameterizedPoolIterator_wrong_pool_exception():
    """
    Test subclass exceptions when instantiated with wrong pool type. If fails,
    ._validate_pool_type or a subclass's _pool_type property is malfunctioning.
    """

    class DummyPool:
        pass

    pool = DummyPool()

    for subclass in DEFAULT_POOL_MAP.values():
        mapping = {DummyPool: subclass}

        with pytest.raises(ParameterSamplerError):
            ParameterizedPoolIterator(pool, pool_map=mapping)


def test_ParameterizedPoolIterator_pool_template_mutation():
    """
    Test that parameter iteration doesn't mutate the pool template.
    """

    class DummyPool:
        def __init__(self):
            self.a = 0
            self.b = 0

    class DummyParamSampler(ParameterizedPoolIterator):
        @property
        def _pool_type(self):
            return DummyPool

    pool = DummyPool()
    variable_params = {"a": [1, 2], "b": [3, 4]}
    mapping = {DummyPool: DummyParamSampler}

    param_sampler = ParameterizedPoolIterator(pool, variable_params, pool_map=mapping)

    for pool_sample, pool_params in param_sampler:
        assert param_sampler.pool_template.a == 0
        assert param_sampler.pool_template.b == 0


def test_ParameterizedPoolIterator_no__params():
    """
    Test that .parameter_sequence uses fixed params when variable params are omitted,
    and [None] when all parameters are omitted.
    """

    class DummyPool:
        def __init__(self):
            self.a = 0
            self.b = 0

    class DummyParamSampler(ParameterizedPoolIterator):
        @property
        def _pool_type(self):
            return DummyPool

    pool = DummyPool()
    mapping = {DummyPool: DummyParamSampler}
    fixed_params = {"a": 1, "b": 2}

    # No variable params
    param_sampler = ParameterizedPoolIterator(
        pool, fixed_params=fixed_params, pool_map=mapping
    )

    assert param_sampler.parameter_sequence == [fixed_params]

    # No params
    param_sampler = ParameterizedPoolIterator(pool, pool_map=mapping)
    assert param_sampler.parameter_sequence == [None]


@given(*make_parameter_strats(POOL_PARAMS))
@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_ParameterizedPoolIterator_curve_pool(
    sim_curve_pool, variable_params, fixed_params
):
    """Tests full instantiation of ParameterizedCurvePoolIterator from SimCurvePool."""
    _test_ParameterizedPoolIterator(sim_curve_pool, variable_params, fixed_params)


@given(*make_parameter_strats(METAPOOL_PARAMS))
@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_ParameterizedPoolIterator_curve_meta_pool(
    sim_curve_meta_pool, variable_params, fixed_params
):
    """Tests full instantiation of ParameterizedCurveMetaPoolIterator from SimCurveMetaPool."""

    def fixed_virtual_price():
        return 10**18

    sim_curve_meta_pool.basepool.get_virtual_price = fixed_virtual_price

    _test_ParameterizedPoolIterator(sim_curve_meta_pool, variable_params, fixed_params)


@given(*make_parameter_strats(METAPOOL_PARAMS))
@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_ParameterizedPoolIterator_curve_rai_pool(
    sim_curve_rai_pool, variable_params, fixed_params
):
    """Tests full instantiation of ParameterizedCurveMetaPoolIterator from SimCurveRaiPool."""

    def fixed_virtual_price():
        return 10**18

    sim_curve_rai_pool.basepool.get_virtual_price = fixed_virtual_price

    _test_ParameterizedPoolIterator(sim_curve_rai_pool, variable_params, fixed_params)


@given(*make_parameter_strats(CRYPTOPOOL_PARAMS))
@settings(
    max_examples=5,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_ParameterizedPoolIterator_curve_crypto_pool(
    sim_curve_crypto_pool, variable_params, fixed_params
):
    """Tests full instantiation of ParameterizedCurveCryptoPoolIteratorfrom SimCurveCryptoPool."""
    _test_ParameterizedPoolIterator(
        sim_curve_crypto_pool, variable_params, fixed_params
    )


# Helper functions for tests
def _test_ParameterizedPoolIterator(pool, variable_params, fixed_params, pool_map=None):
    """
    Tests correct instantiation of a ParameterizedPoolIterator subclass, including
    correct class and parameters/attributes.
    """
    param_sampler = ParameterizedPoolIterator(
        pool, variable_params, fixed_params, pool_map
    )

    pool_to_sampler = pool_map or DEFAULT_POOL_MAP
    expected_type = pool_to_sampler[type(pool)]

    assert isinstance(param_sampler, expected_type)

    _test_pool_params(param_sampler.pool_template, fixed_params)
    _test_ParameterizedPoolIterator_parameter_sequence(param_sampler, variable_params)
    _test_ParameterizedPoolIterator_iterations(param_sampler)


def _test_pool_params(pool, params):
    """
    Tests that pool attributes match those defined in the params dict.
    """
    for key, val in params.items():
        _pool, _key = parse_pool_attribute(pool, key)

        if _key == "D":
            if isinstance(pool, SimCurveCryptoPool):
                D_from_xp = newton_D(_pool.A, _pool.gamma, _pool._xp())
                assert abs(_pool.D - val) <= 10**10
                assert (
                    abs(D_from_xp - val) <= 10**10
                )  # _newton_D allows some minor error

            else:
                D = _pool.D()
                assert abs(D - val) <= 3

        else:
            assert getattr(_pool, _key) == val


def _test_ParameterizedPoolIterator_parameter_sequence(param_sampler, variable_params):
    """
    Tests that param_sampler.parameter_sequence has the expected properties for the
    product of the input variable params.
    """

    param_sequence = param_sampler.parameter_sequence
    param_keys, param_values = zip(*variable_params.items())

    # Test expected number of combinations
    lengths = [len(vals) for vals in param_values]
    length_product = prod(lengths)
    assert len(param_sequence) == length_product

    # Test all keys present in each dict
    input_keys = variable_params.keys()
    for params in param_sequence:
        assert params.keys() == input_keys  # note: undordered equality

    # Test no duplicate entries
    for params1 in param_sequence:
        same_entry_count = 0
        for params2 in param_sequence:
            if params1 == params2:
                same_entry_count += 1
        assert same_entry_count == 1

    # Test expected count of each parameter value
    all_param_values = {key: [dct[key] for dct in param_sequence] for key in param_keys}
    for key, values in variable_params.items():
        param_list = all_param_values[key]
        expected_repeats = length_product / len(values)
        for val in values:
            assert param_list.count(val) == expected_repeats


def _test_ParameterizedPoolIterator_iterations(param_sampler):
    """
    Tests that .parameter_sequence is applied to pool on each iter.
    """
    sequences = zip(param_sampler, param_sampler.parameter_sequence)

    for (pool_sample, pool_params), sampler_params in sequences:
        assert pool_params == sampler_params  # test if correct vals
        _test_pool_params(pool_sample, pool_params)  # test if vals applied to pool


def parse_pool_attribute(pool, attribute):
    """
    Helper function to route "_base" attributes to basepool if necessary.
    """
    if attribute.endswith("_base"):
        return pool.basepool, attribute[:-5]

    return pool, attribute
