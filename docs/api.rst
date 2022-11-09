.. _api:

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

    .. autoclass:: curvesim.pipelines.arbitrage.Metrics
        :members: update, __call__
        :exclude-members: __init__, __new__

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


