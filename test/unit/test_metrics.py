from copy import deepcopy

import pytest
from pandas import DataFrame, Series

from curvesim.exceptions import MetricError
from curvesim.metrics import init_metrics, metrics
from curvesim.metrics.base import Metric, PoolMetric, PricingMetric, get_coin_pairs

all_metrics = [getattr(metrics, m) for m in metrics.__all__]


def test_init_metrics(
    sim_curve_pool, sim_curve_crypto_pool, sim_curve_meta_pool, sim_curve_rai_pool
):
    """Test that all metrics successfully initialize with correct attributes/properties."""

    pools = [
        sim_curve_pool,
        sim_curve_crypto_pool,
        sim_curve_meta_pool,
        sim_curve_rai_pool,
    ]

    coin_names = ["COIN0", "COIN1"]
    coin_addresses = ["0x0", "0x1"]
    prices = {("COIN0", "COIN1"): 10}

    metadata = {
        "coins": {
            "names": coin_names,
            "addresses": coin_addresses,
        },
        "chain": "mainnet",
    }

    basepool_metadata = {
        "coins": {
            "names": [coin_names[-1]],
            "addresses": [coin_addresses[-1]],
        },
        "chain": "mainnet",
    }

    for pool in pools:
        # Set metadata
        pool.metadata = metadata
        if hasattr(pool, "basepool"):
            pool.basepool.metadata = basepool_metadata

        # Loop through metric tests
        metrics = init_metrics(all_metrics, pool=pool)
        for metric in metrics:
            _test_metric_class_init(metric)

            if isinstance(metric, PoolMetric):
                _test_pool_metric_class_init(metric, pool)

            if isinstance(metric, PricingMetric):
                _test_pricing_metric_class_init(metric, coin_names, prices)


def _test_metric_class_init(metric):
    """Test correct mapping of properties for Metric (sub)class."""
    assert metric.metric_function == metric.config["functions"]["metrics"]
    assert metric.plot_config == metric.config.get("plot", None)
    assert metric.summary_functions == metric.config["functions"].get("summary", None)


def _test_pool_metric_class_init(metric, pool):
    """Test properties and methods specific to PoolMetric (sub)class."""

    # Test properties
    assert metric._pool == pool
    assert metric.config == metric.pool_config[type(pool)]

    # Test set_pool
    pool_copy = deepcopy(pool)
    metric.set_pool(pool_copy)
    assert metric._pool == pool_copy
    assert metric._pool != pool

    # Test set_pool_state
    metric.set_pool_state({"A": 0})
    assert metric._pool.A == 0
    if hasattr(pool, "basepool"):
        metric.set_pool_state({"A_base": 0})
        assert metric._pool.basepool.A == 0


def _test_pricing_metric_class_init(metric, coin_names, prices):
    """Test attributes and methods specific to PricingMetric (sub)class."""

    # Test PricingMetric attributes
    assert metric.numeraire == coin_names[0]

    # Test get_market_price
    assert metric.get_market_price("COIN0", "COIN1", prices) == 10
    assert metric.get_market_price("COIN1", "COIN0", prices) == 1 / 10


def test_get_poin_pairs():
    """Test that get_coin_pairs returns same results regardless of input format."""
    price_dict = {("COIN0", "COIN1"): 10}
    price_df = DataFrame.from_records([price_dict])
    price_df2 = DataFrame.from_records([price_dict, price_dict])
    price_series = Series(price_dict)

    formats = [price_dict, price_df, price_df2, price_series]

    for i in range(len(formats) - 1):
        format1 = get_coin_pairs(formats[i])
        format2 = get_coin_pairs(formats[i + 1])
        assert format1 == format2
        assert type(format1) == type(format2)


def test_get_coin_pairs_wrong_type():
    """Test that unsupported input type raises error."""
    inputs = ["123", 123, [1, 2, 3], (1, 2, 3), {1, 2, 3}]

    for inp in inputs:
        with pytest.raises(MetricError):
            get_coin_pairs(inp)


def test_missing_metric_function_exception():
    """Test that metric with no metric_function raises error."""

    class WorkingDummyMetric(Metric):
        @property
        def config(self):
            return {"functions": {"metrics": "working_function"}}

    class BrokenDummyMetric(Metric):
        @property
        def config(self):
            return {"functions": {}}

    metric1 = WorkingDummyMetric()
    metric2 = BrokenDummyMetric()

    assert metric1.metric_function == "working_function"
    with pytest.raises(MetricError):
        metric2.metric_function
