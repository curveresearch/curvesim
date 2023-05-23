"""
Tools for implementing and running simulation pipelines.

Pipelines iterate over pools with parameters set by
:mod:`curvesim.iterators.param_samplers` and time-series data produced by
:mod:`curvesim.iterators.price_samplers`. Each pipeline implements a
"strategy" dictating what is done at each timestep e.g., :class:`.Strategy`.

Typically, a pipeline takes in :class:`~curvesim.pool_data.metadata.PoolMetaDataInterface`;
specifies a param_sampler, price_sampler, and strategy; and returns metrics/results.
"""
