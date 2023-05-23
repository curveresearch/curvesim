.. role:: python(code)
   :language: python

:tocdepth: 2

.. _advanced:

Advanced Usage
==============

.. _metric-configuration:

Adding Custom Metrics
---------------------

Advanced users may wish to create their own metrics to be recorded during a
simulation. This can be achieved by creating a new metric class in
:code:`curvesim.metrics.metrics`. This involves three main components:

1. Subclassing one of the `Generic Metric Classes`_ found in :mod:`curvesim.metrics.base`.
2. `Adding Methods`_ to compute the metric(s).
3. Specifying the `Metric Configuration`_ in the :code:`config` property.

Each component is described in detail below. With these completed, the new metric 
class can be passed to a :mod:`.pipeline`, such as 
[link to volume limited arbitrage pipeline], where it will be automatically 
initialized and included in the :class:`SimResults` output. 

Basic Example
^^^^^^^^^^^^^
The :class:`Timestamp` metric provides a simple introductory example that
incorporates each of the required elements. It subclasses the generic 
:class:`Metric<curvesim.metrics.base.Metric>` class, adds the 
:func:`_get_timestamp()` method, and defines a minimal :code:`config` property 
that specifies :func:`_get_timestamp()` as the function used to generate the 
metric::

   class Timestamp(Metric):
       """Simple pass-through metric to record timestamps."""

       @property
       def config(self):
           return {"functions": {"metrics": self._get_timestamp}}

       def _get_timestamp(self, price_sample, **kwargs):
           return DataFrame(price_sample.timestamp)

While this metric simply "passes through" the timestamps recorded throughout
each simulation run, the :func:`_get_timestamp()` method could clearly be 
replaced to compute something more interesting. The following sections explain 
how each component can be expanded to generate more informative metrics.

Generic Metric Classes
^^^^^^^^^^^^^^^^^^^^^^
Each metric is a subclass of one of four generic classes found in 
:mod:`curvesim.metrics.base`. When creating a new metric, you should subclass
whichever best suits your requirements:

1. :class:`Metric<curvesim.metrics.base.Metric>`
    The most basic of the generic metric classes. Used for metrics that are
    computed with a single function, regardless of the type of pool used in a 
    simulation.

2. :class:`PoolMetric<curvesim.metrics.base.PoolMetric>`
    Generic metric class with distinct configurations for different pool-types. 
    Used for metrics that require unique functions or configurations depending 
    on the type of pool used in a simulation. See `Pool Config Specification`_

3. :class:`PricingMetric<curvesim.metrics.base.PricingMetric>`
    Basic :class:`Metric<curvesim.metrics.base.Metric>` class with added
    functionality for calculations involving market prices.
    In particular, this includes:

    - :func:`get_market_price()<curvesim.metrics.base.PricingMetric.get_market_price>`
       Returns exchange rate for two coins identified by their pool indices.

    - :code:`numeraire` and :code:`numeraire_idx` attributes: 
       The numeraire to be used in pricing calculations and its numeric coin 
       index. The numeraire is automatically selected from a list of preferred 
       numeraires, or defaults to the first of the :code:`coin_names` passed to 
       the metric at instantiation. See :func:`curvesim.metrics.base.get_numeraire`.


4. :class:`PoolPricingMetric<curvesim.metrics.base.PoolPricingMetric>`
    :class:`PoolMetric<curvesim.metrics.base.PoolMetric>` class with added
    functionality for calculations involving market prices (same as above).

Adding Methods
^^^^^^^^^^^^^^
The method(s) for computing the metric(s)

-can return multiple sub-metrics
-must return a dataframe with columns matching the sub-metric names given in config
-convenient to group based on data requirements
-explain the data context (statelog)
-explain updating the pool state
-handling kwargs












Metric Configuration
^^^^^^^^^^^^^^^^^^^^

.. include:: metric_config.rst
