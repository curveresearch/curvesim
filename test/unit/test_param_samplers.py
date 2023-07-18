import pytest

from hypothesis import given, settings
from hypothesis import strategies as st
from pandas import DataFrame

from itertools import product

from curvesim.exceptions import ParameterSamplerError
from curvesim.iterators.param_samplers import ParameterizedPoolIterator
from curvesim.iterators.param_samplers.parameterized_pool_iterator import (
    DEFAULT_POOL_MAP,
)
from curvesim.pool.sim_interface import SimCurvePool, SimCurveRaiPool, SimCurveMetaPool
from curvesim.iterators.param_samplers.parameterized_pool_iterator import (
    ParameterizedCurveCryptoPoolIterator,
)  # Remove
from curvesim.pool.cryptoswap import CurveCryptoPool  # Remove

SimCurveCryptoPool = CurveCryptoPool  # Remove

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
            val_strat = to_list_strat(val_strat)
        dict_subset[key] = draw(val_strat)

    return dict_subset


def to_list_strat(strategy, min_size=2, max_size=20):
    """Makes list strategy from input strategy"""
    return st.lists(strategy, min_size=min_size, max_size=max_size, unique=True)


# Tests
def test_invalid_parameter_exceptions():
    """
    Test exceptions for invalid parameter names. If fails,
    ParameterSampler._validate_attributes is malfunctioning.
    """
    pool = POOLS[SimCurvePool]

    # Not a pool param
    with pytest.raises(ParameterSamplerError):
        ParameterizedPoolIterator(pool, {"not_a_param": [20, 30]})

    # Basepool param when no basepool
    with pytest.raises(ParameterSamplerError):
        ParameterizedPoolIterator(pool, {"A_base": [10, 100]})


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
    variable_params = {"a": [1, 2], "b": [3, 4]}

    with pytest.raises(ParameterSamplerError):
        ParameterizedPoolIterator(pool, variable_params)


def test_ParameterizedPoolIterator_wrong_pool_exception():
    """
    Test subclass exceptions when instantiated with wrong pool type. If fails,
    ._validate_pool_type or a subclass's _pool_type property is malfunctioning.
    """

    class DummyPool:
        pass

    pool = DummyPool()
    variable_params = {"a": 1, "b": 2}

    for subclass in DEFAULT_POOL_MAP.values():
        mapping = {DummyPool: subclass}

        with pytest.raises(ParameterSamplerError):
            ParameterizedPoolIterator(pool, variable_params, pool_map=mapping)


@given(*make_parameter_strats(POOL_PARAMS))
@settings(max_examples=5, deadline=None)
def test_ParameterizedPoolIterator_curve_pool(variable_params, fixed_params):
    """Tests full instantiation of ParameterizedCurvePoolIterator from SimCurvePool."""
    _test_ParameterizedPoolIterator(SimCurvePool, variable_params, fixed_params)


@given(*make_parameter_strats(METAPOOL_PARAMS))
@settings(max_examples=5, deadline=None)
def test_ParameterizedPoolIterator_curve_meta_pool(variable_params, fixed_params):
    """Tests full instantiation of ParameterizedCurveMetaPoolIterator from SimCurveMetaPool."""
    _test_ParameterizedPoolIterator(SimCurveMetaPool, variable_params, fixed_params)


@given(*make_parameter_strats(METAPOOL_PARAMS))
@settings(max_examples=5, deadline=None)
def test_ParameterizedPoolIterator_curve_rai_pool(variable_params, fixed_params):
    """Tests full instantiation of ParameterizedCurveMetaPoolIterator from SimCurveRaiPool."""
    _test_ParameterizedPoolIterator(SimCurveRaiPool, variable_params, fixed_params)


@given(*make_parameter_strats(CRYPTOPOOL_PARAMS))
@settings(max_examples=5, deadline=None)
def test_ParameterizedPoolIterator_curve_crypto_pool(variable_params, fixed_params):
    """Tests full instantiation of ParameterizedCurveCryptoPoolIteratorfrom SimCurveCryptoPool."""
    ParameterizedCurveCryptoPoolIterator._pool_type = (
        SimCurveCryptoPool  # remove when SimPool ready
    )
    pool_map = {
        SimCurveCryptoPool: ParameterizedCurveCryptoPoolIterator
    }  # remove when SimPool ready
    _test_ParameterizedPoolIterator(
        SimCurveCryptoPool, variable_params, fixed_params, pool_map=pool_map
    )


# Helper functions for tests
def _test_ParameterizedPoolIterator(
    pool_type, variable_params, fixed_params, pool_map=None
):
    """
    Tests correct instantiation of a ParameterizedPoolIterator subclass, including
    correct class and parameters/attributes.
    """
    pool = POOLS[pool_type]
    param_sampler = ParameterizedPoolIterator(
        pool, variable_params, fixed_params, pool_map
    )

    pool_to_sampler = pool_map or DEFAULT_POOL_MAP
    expected_type = pool_to_sampler[pool_type]

    assert isinstance(param_sampler, expected_type)
    assert pool != param_sampler.pool_template  # ensure deepcopy

    _test_pool_params(param_sampler.pool_template, fixed_params)
    _test_ParameterizedPoolIterator_variable_params(param_sampler, variable_params)


def _test_pool_params(pool, params):
    """
    Tests that pool attributes match those defined in the params dict.
    """
    for key, val in params.items():
        _pool, _key = parse_pool_attribute(pool, key)

        if _key == "D":
            if hasattr(_pool, "_newton_D"):  # v2 pools
                D = _pool._newton_D(_pool.A, _pool.gamma, _pool._xp())
                assert abs(D - val) <= 10**10  # _newton_D allows some minor error

            else:
                D = _pool.D()
                assert abs(D - val) <= 3

        else:
            assert getattr(_pool, _key) == val


def _test_ParameterizedPoolIterator_variable_params(param_sampler, variable_params):
    """
    Tests that .parameter_sequence is generated and applied to pool on each iter.
    """
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

crypto_kwargs = {
    "A": 400000,
    "gamma": 72500000000000,
    "n": 2,
    "precisions": [1, 1],
    "mid_fee": 26000000,
    "out_fee": 45000000,
    "allowed_extra_profit": 2000000000000,
    "fee_gamma": 230000000000000,
    "adjustment_step": 146000000000000,
    "admin_fee": 5000000000,
    "ma_half_time": 600,
    "price_scale": 1550997347493624157,
    "balances": [20477317313816545807568241, 13270936465339000000000000],
    "tokens": 1550997347493624157,
    "xcp_profit": 1052829794354693246,
    "xcp_profit_a": 1052785575319598710,
}

POOLS = {
    SimCurvePool: SimCurvePool(A=250, D=1000000 * 10**18, n=2, admin_fee=5 * 10**9),
    SimCurveMetaPool: SimCurveMetaPool(**meta_kwargs),
    SimCurveRaiPool: SimCurveRaiPool(**meta_kwargs, redemption_prices=rp),
    SimCurveCryptoPool: SimCurveCryptoPool(**crypto_kwargs),
}
