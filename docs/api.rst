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


Curve Pools
-----------

.. _poolapi:

.. automodule:: curvesim.pool

.. autofunction:: curvesim.pool.get
.. autofunction:: curvesim.pool.make

.. autoclass:: curvesim.pool.Pool
   :inherited-members:

.. autoclass:: curvesim.pool.CurvePool
   :members:

.. autoclass:: curvesim.pool.CurveMetaPool
   :members:

.. autoclass:: curvesim.pool.CurveRaiPool
   :members:


.. Pool Plots
.. ----------
.. 
.. .. _poolviewersapi:
.. 
.. .. autofunction:: curvesim.bonding_curve
.. .. autofunction:: curvesim.order_book


Simulation functions
--------------------

.. _simapi:

.. automodule:: curvesim.sim

.. autofunction:: curvesim.sim.autosim


Simulation Pipelines
---------------------
.. _pipelinesapi:

.. automodule:: curvesim.pipelines
    :members:
    :exclude-members: wrapped_strategy

.. autoclass:: curvesim.templates.Strategy
    :members:
.. autoclass:: curvesim.templates.Trader
    :members:
.. autoclass:: curvesim.templates.SimPool
    :members:

    Simple arbitrage
    -----------------
    .. automodule:: curvesim.pipelines.simple

    .. autofunction:: curvesim.pipelines.simple.pipeline

    .. autoclass:: curvesim.pipelines.simple.strategy.SimpleStrategy
        :members:
        :exclude-members: __init__, __new__, trader_class, state_log_class
        :private-members: _get_trader_inputs

    .. autoclass:: curvesim.pipelines.simple.trader.SimpleArbitrageur
        :members:
        :private-members:

    Volume-limited arbitrage
    ------------------------
    .. automodule:: curvesim.pipelines.vol_limited_arb

    .. autofunction:: curvesim.pipelines.vol_limited_arb.pipeline

    .. autoclass:: curvesim.pipelines.vol_limited_arb.strategy.VolumeLimitedStrategy
        :members:

    .. autoclass:: curvesim.pipelines.vol_limited_arb.trader.VolumeLimitedArbitrageur
        :members:


Pool Data
----------

.. _pooldataapi:

.. automodule:: curvesim.pool_data
    :members:

.. autofunction:: curvesim.pool_data.metadata.PoolMetaData
.. autoclass:: curvesim.pool_data.metadata.PoolMetaDataInterface
    :members:


Subgraph
--------

.. _subgraphapi:

Curve
******
Used to pull pool state data and historical volume data.

.. autofunction:: curvesim.network.subgraph.pool_snapshot
.. autofunction:: curvesim.network.subgraph.volume

Reflexer
********
Used to pull RAI redemption prices when simulating the RAI metapool.

.. autofunction:: curvesim.network.subgraph.redemption_prices



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

    Abstract
    ^^^^^^^^^
    .. autoclass:: curvesim.templates.param_samplers.ParameterSampler
        :members:
        :special-members: __iter__

    .. autoclass:: curvesim.templates.param_samplers.SequentialParameterSampler
        :special-members: __iter__
        :inherited-members:

    Concrete
    ^^^^^^^^^
    .. autoclass:: curvesim.iterators.param_samplers.Grid
        :special-members: __iter__
        :inherited-members:

    .. class:: curvesim.iterators.param_samplers.CurvePoolGrid

        :class:`Grid` parameter sampler specialized for Curve pools.


    .. class:: curvesim.iterators.param_samplers.CurveMetaPoolGrid

        :class:`Grid` parameter sampler specialized for Curve meta-pools.

    .. class:: curvesim.iterators.param_samplers.CurveCryptoPoolGrid

        :class:`Grid` parameter sampler specialized for Curve crypto pools.

    Price Samplers
    --------------

    .. automodule:: curvesim.iterators.price_samplers

    Abstract
    ^^^^^^^^^

    .. autoclass:: curvesim.templates.price_samplers.PriceSampler
        :members:
        :special-members: __iter__

    .. autoclass:: curvesim.templates.price_samplers.PriceSample
        :members:
        :exclude-members: __init__, __new__

    Concrete
    ^^^^^^^^^

    .. autoclass:: curvesim.iterators.price_samplers.PriceVolume
        :special-members: __iter__
        :inherited-members:

    .. autoclass:: curvesim.iterators.price_samplers.PriceVolumeSample
        :members:
        :exclude-members: __init__, __new__


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

Plot
----

.. _plotapi:

.. automodule:: curvesim.plot

.. autoclass:: curvesim.plot.ResultPlotter
    :members:

.. autoclass:: curvesim.plot.altair.AltairResultPlotter
    :members:
    :exclude-members: __init__, __new__, save




