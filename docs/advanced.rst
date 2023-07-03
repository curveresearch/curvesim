.. role:: python(code)
   :language: python

:tocdepth: 2



Advanced Usage
==============

.. _advanced:


Adding Custom Simulation
-------------------------

.. _adding-simulation:


A simulation consists of a *pipeline* taking in pool configurations
and market data sampled as a time-series.  For each pool configuration, a *run*
consists of applying the strategy to the given configuration and stream of market
data.  A report of various metrics can then be created from the results of all
runs.

To flexibly handle future-use-cases, the pipeline concept has not been formalized into
a configurable object, but the basic template can be understood in the implementation
of the helper function :func:`run_pipeline`.  It takes in a
:mod:`param sampler <curvesim.iterators.param_samplers>`,
:mod:`price sampler <curvesim.iterators.price_samplers>`,
and :class:`strategy <curvesim.pipeline.templates.Strategy>`.
The pipeline iterates over the pool with parameters set from the param sampler; for each
set of parameters, the strategy is applied on each time series sample produced by the
price sampler.

Typically you would use :func:`run_pipeline` by creating a function that:

1. instantiates :class:`~curvesim.pool_data.metadata.PoolMetaDataInterface` from a pool address and chain label

2. creates a :class:`~curvesim.pool.sim_interface.SimPool` using the pool data.

3. instantiates a param_sampler, price_sampler, and strategy

4. invokes :func:`run_pipeline`, returning result metrics

Other auxiliary args may need to be passed-in to instantiate all necessary objects.

The main pipeline, which was developed for the specific use-case of optimizing Curve pools
for best reward-risk tradeoff, is the
:mod:`volume limited arbitrage pipeline <curvesim.pipelines.vol_limited_arb>`.

The :mod:`simple pipeline <curvesim.pipelines.simple>` provides an easier starting
point for creating a custom pipeline.


The :code:`SimPool` interface
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To setup arbitrage strategies, the :class:`~curvesim.pipelines.templates.SimPool` interface exposes::

1. :code:`price`: *(method)*

2. :code:`trade`: *(method)*

3. :code:`assets`: *(property)*

Given market price(s), any strategy that checks the "price" and then exchanges one
asset for another can be implemented.  While the name :code:`SimPool` suggests a pool, this object
can be any type of market or venue where assets are exchanged.

For example, one could implement::

    class CollateralizedDebtPosition(SimPool):
        """
        A simple Aave-style collateralized debt position.
        """

        def price(self, debt_token, collateral_token, use_fee=True):
            """
            Returns the effective price for collateral from liquidating
            the position.
            """

        def trade(self, debt_token, collateral_token, size):
            """
            Liquidate the position by paying `size` amount of the debt.
            """

        @property
        def assets(self):
            """
            Return a :class:`SimAssets` instance with information on
            the tradable assets (debt and collateral in this example).
            """


The available implementations wrap a Curve pool into an appropriate :code:`SimPool`, letting
strategies more flexibly define tradable assets.  Expected use-cases taking advantage
of these abstractions include trading LP tokens or even baskets of tokens, routing through
multiple pools, and trading between two competing pools of different types.


The :code:`Strategy` and :code:`Trader` interfaces
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :class:`~curvesim.pipeline.templates.Strategy` callable is what coordinates the different moving parts of the system::

    def __call__(self, sim_pool, parameters, price_sampler):
        """
        Computes and executes trades at each timestep.
        """

The parameters configure the pool and the :code:`price_sampler` provides market tick data that pushes the pool through a simulation run.

The :code:`Strategy` base class houses an implementation to do this based on customizing an injected :class:`~curvesim.pipelines.templates.Trader`.  The :code:`Trader` class assumes typical logic has a compute step and then a trade execution step, but since only the :code:`process_time_sample` method is invoked in a strategy, this isn't mandatory in your custom implementation.


The Param and Price Samplers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^




Adding Custom Metrics
---------------------

.. _adding-metrics:

Custom simulation metrics can be created by adding new metric classes to
:code:`curvesim.metrics.metrics`. This involves three main requirements:

1. Subclassing one of the `Generic Metric Classes`_ found in :mod:`curvesim.metrics.base`.
2. `Adding Methods`_ to compute the metric(s).
3. Specifying the `Metric Configuration`_ in the :code:`config` property.

Each requirement is described in detail below. Once completed, the new 
metric class can be passed to a simulation :mod:`pipeline<.pipelines>`, where it 
will be automatically initialized, calculated, and included in the 
:class:`results<.metrics.SimResults>` output. 

Basic Example
^^^^^^^^^^^^^
The :class:`Timestamp` metric provides a simple example that incorporates each 
of the required elements. It subclasses the generic 
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
each simulation run, any of the major components could be modified to produce 
something more interesting. The following sections explain how each component 
can be expanded to generate more informative metrics.

Generic Metric Classes
^^^^^^^^^^^^^^^^^^^^^^
Each metric is a subclass of one of four generic classes found in 
:mod:`curvesim.metrics.base`. When creating a new metric, you should subclass
whichever best suits your needs:

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
    functionality for calculations involving market prices:

    - :func:`get_market_price()<curvesim.metrics.base.PricingMetric.get_market_price>`
       Returns exchange rate for two coins identified by their pool indices.

    - :code:`numeraire` and :code:`numeraire_idx` attributes: 
       The numeraire to be used in pricing calculations and its numeric coin 
       index. The numeraire is automatically selected from a list of preferred 
       numeraires, or defaults to the first of the :code:`coin_names` passed to 
       the metric at instantiation. See 
       :func:`curvesim.metrics.base.get_numeraire`.


4. :class:`PoolPricingMetric<curvesim.metrics.base.PoolPricingMetric>`
    :class:`PoolMetric<curvesim.metrics.base.PoolMetric>` class with added
    functionality for calculations involving market prices (same as above).

Adding Methods
^^^^^^^^^^^^^^
Methods for computing (and, optionally, summarizing) your metric(s) should be 
added to your new subclass and 
:ref:`referenced in the config property<function-config>`.

Metric Function *(required)*
.............................

The function for computing your metric(s) is executed at the end of each 
simulation run (i.e., after each timepoint is simulated with a given set of pool
parameters). The function should take the 
:ref:`data provided by the StateLog<metric-inputs>` and return a DataFrame with
named columns for each computed metric ("sub-metric") and rows for each timestamp. 

If :ref:`summary functions<function-config>` or 
:ref:`plotting specs<plot-config>` are included in the config property, they 
must reference each sub-metric using the column names used in the DataFrame.

Data Inputs
...........

.. _metric-inputs:

At the end of each simulation run, the :class:`.StateLog` passes the following
data to each metric as keyword arguments. Your function signature should include
any of the keywords you need for your computation and :code:`**kwargs` to "soak up"
any unused keywords.

- :code:`pool_parameters` *(DataFrame)*
   The parameters of the pool used in a simulation run. These vary depending 
   on pool type (e.g., for a stableswap pool, these are A, initial D, and fee), 
   and are returned in a DataFrame with columns for each parameter. For example::

           A             D     fee
        0  100  3.882173e+08  0.0004

   See :code:`metrics.StateLog.pool_parameters` for the parameters recorded for 
   each pool type.

- :code:`pool_state` *(DataFrame)*
   A time series of the pool state recorded at each timepoint in the simulation
   run. For example::

          balances                                           tokens
    0     [130845201307275888876149751, 1305944797254687...  378440487077049660301217105
    1     [132282500493342273867963383, 1317798299188966...  378440487077049660301217105
    2     [133706765982576658123938807, 1329505526946925...  378440487077049660301217105
    3     [135129521787669164155296759, 1341178732597889...  378440487077049660301217105
    4     [136553908964358298693622775, 1352866792170694...  378440487077049660301217105
    ...                                                 ...                          ...
    1460  [130546859394920751460984594, 1294035642077598...  378440487077049660301217105 
    1461  [130546859394920751460984594, 1294035642077598...  378440487077049660301217105
    1462  [129676139388539620009120586, 1303866269827065...  378440487077049660301217105
    1463  [130515100587653360449688394, 1302453178645099...  378440487077049660301217105
    1464  [129771580655313918569313433, 1302453178645094...  378440487077049660301217105


   The recorded variables vary with pool type. See 
   :code:`metrics.StateLog.pool_state` for the parameters recorded for each pool type.

   .. note::
      If your calculations depend on pool state, you must call
      :python:`self.set_pool_state(pool_state_row)` before performing a calculation
      for each timestamp. :func:`set_pool_state` is a built-in method in the
      :class:`PoolMetric<curvesim.metrics.base.PoolMetric>` class, and takes one row
      of the :code:`pool_state` DataFrame as input for each timestamp.


- :code:`price_sample` *(DataFrame)*
   The information provided by the 
   :class:`price_sampler<curvesim.iterators.price_samplers>` at each timepoint.
   Currently, this includes the timestamp, market prices, and market volumes.
   Prices and volumes are given for each pairwise combination of coins, ordered
   as in :code:`itertools.combinations(range(n_coins), 2)`::

             timestamp                  prices                                        volumes
        0    2023-03-23 23:30:00+00:00  [0.9972223936856817, 0.9934336361010216, ...  [6372460371.611408, 32388718876.53451,  ...
        1    2023-03-24 00:30:00+00:00  [0.9974647037626924, 0.9953008467903304, ...  [6405220209.779885, 32298840369.832382, ...
        2    2023-03-24 01:30:00+00:00  [0.9983873712830038, 0.9968781445095656, ...  [6428761178.953415, 31924323767.57396,  ...
        3    2023-03-24 02:30:00+00:00  [0.998974908950286, 0.9971146840056136,  ...  [6478213966.455348, 31834217713.8281,   ...
        4    2023-03-24 03:30:00+00:00  [0.9954604997820208, 0.993597773487017,  ...  [6476018037.815129, 31880343748.124725, ...
        ...                        ...                                           ...                                          ...
        1460 2023-05-23 19:30:00+00:00  [0.9995590221398217, 0.9996802980794983, ...  [2450447658.4796195, 19720280583.1984,  ...
        1461 2023-05-23 20:30:00+00:00  [0.999792588099074, 0.9998231064202561,  ...  [3767115607.6887126, 9745029505.401602, ...
        1462 2023-05-23 21:30:00+00:00  [1.002580556630733, 1.001640822363833,   ...  [3238172226.196708, 20213110441.90307,  ...
        1463 2023-05-23 22:30:00+00:00  [0.9992115557645646, 0.9991726268082701, ...  [3806396776.6569495, 18785423624.570637,...
        1464 2023-05-23 23:30:00+00:00  [1.0000347245259464, 1.0001933464807435, ...  [1618332387.3201604, 20024972704.395084,...

- :code:`trade_data` *(DataFrame)*
    The information provided by the pipeline :class:`strategy<curvesim.pipelines.strategy>` at each timepoint.
    Currently, this includes the executed trades (format: coin_in index, coin_out index, coin_in amount, coin_out amount, fee), total
    volume, and post-trade price error between pool price and market price::

              trades                                             volume                     price_errors
        0     [(1, 2, 1425272746997353459744768, 14246897852...  2864693070085621213560832  [0.003204099273566685, 0.005952357013628284, 0...
        1     [(1, 2, 1423136006037754555138048, 14221320488...  2860435192104139546951680  [0.001272223599089517, 0.0037650550769624536, ...
        2     [(1, 2, 1409378240580197696929792, 14079575628...  2833643729814581952905216  [0.00030753025199858897, 0.001863116663974429,...
        3     [(1, 2, 1407807687734395949547520, 14059536943...  2830563492826901980905472  [0.00034208257763679306, 0.0012934752817830297...
        4     [(1, 2, 1409207476296572163063808, 14069028812...  2833594652985706701389824  [2.394374749004058e-05, 0.004466502992504617, ...
        ...                                                 ...                        ...                                                ...
        1460  [(0, 1, 90998886739193884573696, 9096431673643...    90998886739193884573696  [5.417643337612965e-05, -0.0001157222448445738...
        1461                                                 []                          0  [-0.0001793895258761502, -0.000258530585602323...
        1462  [(1, 2, 862811250032832837320704, 862453153772...  1733689111071210703159296  [0.0005053090828606166, 0.001416255647489928, ...
        1463  [(0, 2, 697608304688585215311872, 697307118016...   838961199113740440567808  [0.000331361959104326, 0.0004680864443290522, ...
        1464  [(2, 0, 743639722611787945738240, 743519932339...   743639722612382454775808  [-2.4884112744816278e-05, -2.3648798199493726e...


Summary Functions *(optional)*
..............................

Summary functions take the per-timestamp metrics computed by your metric
function and compute a single value for each run. As outlined 
:ref:`below<function-config>`, summary functions may be specified by a string
referring to a pandas.DataFrame method, or a dict mapping a summary statistic's 
name to a custom function. 

Summary functions are specified individually for each sub-metric computed by 
your metric function (i.e., for each column in the returned DataFrame). 

If you specify a custom summary function, it should take the column of 
per-timestamp values for your sub-metric as an argument and return a single 
value. For example, the :class:`PoolValue` metric takes a pandas.DataFrame as input, 
and returns a single value which summarizes each run::

        def compute_annualized_returns(self, data):
            """Computes annualized returns from a series of pool values."""
            year_multipliers = timedelta64(1, "Y") / data.index.to_series().diff()
            log_returns = log(data).diff()

            return exp((log_returns * year_multipliers).mean()) - 1



.. _metric-configuration:

Metric Configuration
^^^^^^^^^^^^^^^^^^^^

.. include:: metric_config.rst
