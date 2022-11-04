"""
Tools for implementing and running simulation pipelines.

Pipelines iterate over pools with parameters set by
:mod:`.param_samplers` and time-series data produced by :mod:`.price_samplers`.
Each pipeline implements a "strategy" dictating what is done at each timestep
(e.g., see :func:`.pipelines.arbitrage.strategy`).

Typically, a pipeline takes in :class:`pool_data`; specifies a param_sampler,
price_sampler, and strategy; and returns metrics/results.
"""

__all__ = ["arbitrage", "templates", "utils"]
