.. _api:

.. role:: python(code)
   :language: python

Developer Interface
===================

.. module:: curvesim

This documentation covers the exposed public interface for Curvesim,
starting with the primary classes and functions, and drilling down into
the less commonly used.


Simulation functions
--------------------

.. _simapi:

.. automodule:: curvesim.sim

.. autofunction:: curvesim.sim.autosim


Curve Pools
-----------

.. _poolapi:

.. automodule:: curvesim.pool

.. autofunction:: curvesim.pool.get
.. autofunction:: curvesim.pool.make

.. autoclass:: curvesim.pool.Pool
   :inherited-members:

.. autoclass:: curvesim.pool.CurvePool
   :inherited-members:

.. autoclass:: curvesim.pool.CurveMetaPool
   :inherited-members:

.. autoclass:: curvesim.pool.CurveRaiPool
   :inherited-members:


Pool Plots
----------

.. _poolviewersapi:

.. autofunction:: curvesim.bonding_curve
.. autofunction:: curvesim.order_book


Pipelines
---------
.. _pipelinesapi:

.. automodule:: curvesim.pipelines


    Arbitrage
    ---------
    .. autofunction:: curvesim.pipelines.arbitrage.volume_limited_arbitrage()
    .. autofunction:: curvesim.pipelines.arbitrage.strategy()

    .. autoclass:: curvesim.pipelines.arbitrage.Arbitrageur
        :inherited-members:

.. autofunction:: curvesim.pipelines.templates.run_pipeline()

Pool Data
----------

.. _pooldataapi:

.. automodule:: curvesim.pool_data

.. autofunction:: curvesim.pool_data.get()

.. autoclass:: curvesim.pool_data.PoolData
    :inherited-members:

Price Data
-----------

.. _pricedataapi:

.. automodule:: curvesim.price_data

.. autofunction:: curvesim.price_data.get()

Iterators
---------

.. _iteratorsapi:

.. automodule:: curvesim.iterators

    Parameter Samplers
    ------------------
    .. automodule:: curvesim.iterators.param_samplers

    .. autoclass:: curvesim.iterators.param_samplers.Grid
        :inherited-members:

    Price Samplers
    --------------
    .. automodule:: curvesim.iterators.price_samplers

    .. autoclass:: curvesim.iterators.price_samplers.PriceVolume
        :inherited-members:

Metrics
-------

.. _metricsapi:

.. automodule:: curvesim.metrics

    Base & Generic Classes
    ----------------------
    .. automodule:: curvesim.metrics.base

    .. autoclass:: curvesim.metrics.base.MetricBase
        :members:

    .. autoclass:: curvesim.metrics.base.Metric
        :inherited-members:

    .. autoclass:: curvesim.metrics.base.PoolMetric
        :inherited-members:

    .. autoclass:: curvesim.metrics.base.PricingMixin
        :members:

    .. autoclass:: curvesim.metrics.base.PricingMetric
        :inherited-members:

    .. autoclass:: curvesim.metrics.base.PoolPricingMetric
        :inherited-members:



    Specific Metric Classes
    -----------------------
    .. automodule:: curvesim.metrics.metrics

    Metric Log
    ----------
    .. autoclass:: curvesim.metrics.log.MetricLog

    Results
    -------
    .. autoclass:: curvesim.metrics.results.SimResults

    Metric Configuration
    --------------------

    .. include:: metric_config.rst
