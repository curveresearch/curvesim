.. _api:

.. role:: python(code)
   :language: python

:tocdepth: 2


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

.. autofunction:: curvesim.pool_data.get_metadata

.. autofunction:: curvesim.pool_data.get_data_cache

.. autofunction:: curvesim.pool_data.PoolMetaData

.. autoclass:: curvesim.pool_data.PoolDataCache
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
    Specific metrics used in simulations are stored in :code:`curvesim.metrics.metrics`

    State Log
    ---------
    .. autoclass:: curvesim.metrics.StateLog
        :exclude-members: __init__, __new__

    Results
    -------
    .. autoclass:: curvesim.metrics.SimResults
        :members:
        :exclude-members: __init__, __new__

    Metric Configuration
    --------------------

    .. include:: metric_config.rst

Plot
----

.. _plotapi:

.. automodule:: curvesim.plot

.. autoclass:: curvesim.plot.ResultPlotter
    :members:

.. autoclass:: curvesim.plot.altair.AltairResultPlotter
    :members:
    :exclude-members: __init__, __new__, save




