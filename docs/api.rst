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

.. autoclass:: curvesim.pool.MetaPool
   :inherited-members:

.. autoclass:: curvesim.pool.RaiPool
   :inherited-members:


Pipelines
---------
.. _pipelinesapi:

.. automodule:: curvesim.pipelines

    Arbitrage
    ---------
    .. autofunction:: curvesim.pipelines.arbitrage.volume_limited_arbitrage()

Pool Data
----------

.. _pooldataapi:

.. automodule:: curvesim.pool_data

.. autofunction:: curvesim.pool_data.get()

.. autoclass:: curvesim.pool_data.PoolData
    :inherited-members:

Price Data
------------

.. _pricedataapi:

.. automodule:: curvesim.price_data

.. autofunction:: curvesim.price_data.get()
