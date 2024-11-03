"""
Tools for implementing and running simulation pipelines.

The basic model for a pipeline is demonstrated in the implementation of
:func:`run_pipeline`.  It takes in a `param_sampler`, `price_sampler`, and
`strategy`.

Pipelines iterate over pools with parameters set by
:mod:`curvesim.iterators.param_samplers` and time-series data produced by
:mod:`curvesim.iterators.price_samplers`.  At each timestemp, the
the :class:`~curvesim.pipelines.templates.Strategy` dictates what is done.

A typical pipeline implementation is a function taking in whatever market data needed;
pool data such as :class:`~curvesim.pool_data.metadata.PoolMetaDataInterface`;
instantiates a param_sampler, price_sampler, and strategy; and invokes `run_pipeline`,
returning its result metrics.
"""

from billiard import Pool as BilliardPool

from curvesim.logging import (
    configure_multiprocess_logging,
    get_logger,
    multiprocessing_logging_queue,
)

logger = get_logger(__name__)


def run_pipeline(param_sampler, price_sampler, strategy, ncpu=4):
    """
    Core function for running pipelines.

    Typically called within a function specifying the pipeline components
    (see, e.g., :func:`curvesim.pipelines.vol_limited_arb.pipeline`)

    Parameters
    ----------
    param_sampler : iterator
        An iterator that returns pool parameters (see :mod:`.param_samplers`).

    price_sampler : iterator
        An iterator that returns (minimally) a time-series of prices
        (see :mod:`.price_samplers`).

    strategy: callable
        A function dictating what happens at each timestep.

    ncpu : int, default=4
        Number of cores to use.

    Returns
    -------
    results : tuple
        Contains the metrics produced by the strategy.

    """
    if ncpu > 1:
        with multiprocessing_logging_queue() as logging_queue:
            strategy_args_list = [(pool, params, price_sampler) for pool, params in param_sampler]

            wrapped_args_list = [(strategy, logging_queue, *args) for args in strategy_args_list]

            with BilliardPool(ncpu) as clust:
                results = tuple(zip(*clust.starmap(wrapped_strategy, wrapped_args_list)))
                clust.close()
                clust.join()  # coverage needs this

    else:
        results = []
        for pool, params in param_sampler:
            metrics = strategy(pool, params, price_sampler)
            results.append(metrics)
        results = tuple(zip(*results))

    return results


def wrapped_strategy(strategy, logging_queue, *args):
    """
    This wrapper ensures we configure logging to use the
    multiprocessing enqueueing logic within the new process.

    Must be defined at the top-level of the module so it can
    be pickled.
    """
    configure_multiprocess_logging(logging_queue)
    return strategy(*args)
