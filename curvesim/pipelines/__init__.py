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
from abc import ABC
from collections.abc import Iterator
from multiprocessing import Pool as cpu_pool

from curvesim.iterators.param_samplers.parameterized_pool_iterator import (
    ParameterizedPoolIterator,
)
from curvesim.iterators.price_samplers.price_volume import PriceVolume
from curvesim.logging import (
    configure_multiprocess_logging,
    get_logger,
    multiprocessing_logging_queue,
)
from curvesim.metrics.results import make_results
from curvesim.pipelines.common import DEFAULT_METRICS
from curvesim.pool import get_sim_pool
from curvesim.utils import dataclass

logger = get_logger(__name__)


class Clock(ABC):
    pass


@dataclass(frozen=True)
class TimePeriod(Iterator, Clock):
    start: int
    end: int

    def __iter__(self):
        raise NotImplementedError


class FrequencyTimePeriod(TimePeriod):
    freq: str


class ReferenceMarket(ABC):
    def price(self, coin_in, coin_out, timestep):
        raise NotImplementedError


class DataSource:
    pass


class SimAsset:
    pass


@dataclass
class TokenPair(SimAsset):
    base_symbol: str
    quote_symbol: str


@dataclass
class PoolPair(TokenPair):
    pool_address: str
    base_coin_address: str
    quote_coin_address: str


class SingleSourceReferenceMarket(ReferenceMarket):
    """
    The sole data source is typically aggregated data
    from a data provider such as Coingecko or Kaiko.

    This reference market simulates an infinite-depth
    external venue, i.e. we can trade at any size
    at the given price without market impact.
    """

    def __init__(self, sim_assets, data_source, clock):
        ...

    def price(self, coin_in, coin_out, timestep):
        ...


class Pipeline:

    # These classes should be injected in child classes
    # to create the desired behavior.
    reference_market_class = None
    trader_class: Optional[Type[Trader]] = None
    log_class: Optional[Type[Log]] = None

    sim_pool_factory = get_sim_pool

    def __init__(self, pool_metadata, metrics=None):
        pool = get_sim_pool(pool_metadata)
        self.pool = pool
        metrics = metrics or DEFAULT_METRICS
        self.metrics = init_metrics(metrics, pool=pool)

        self.run_outputs = []

        trader = self.trader_class(pool)
        log = self.log_class(pool, self.metrics)

    def run(self, variable_params, fixed_params, ncpu=4):
        pool = self.pool
        strategy = self.strategy
        metrics = self.metrics
        sim_pool_factory = self.sim_pool_factory
        pool_metadata = self.pool_metadata

        reference_market = SingleSourceReferenceMarket(sim_assets, data_source, clock)
        configured_pools = configured_pool_sequence(
            sim_pool_factory, pool_metadata, variable_params
        )

        executor = self.execute_run
        data_per_run, data_per_trade, summary_data = run_pipeline(
            configured_pools, reference_market, executor, ncpu
        )
        self.run_outputs.append((data_per_run, data_per_trade, summary_data))

        results = make_results(*output, metrics)
        self.results.append(results)

    def execute_run(self, pool, parameters, reference_market):
        """
        Computes and executes trades for all the timesteps in a single run.

        Parameters
        ----------
        pool : :class:`~curvesim.pipelines.templates.SimPool`
            The pool to be traded against.

        parameters : dict
            Current pool parameters from the param_sampler (only used for
            logging/display).

        price_sampler : iterable
            Iterable that for each timestep returns market data used by
            the trader.


        Returns
        -------
        metrics : tuple of lists

        """
        trader = self.trader_class(pool)
        log = self.log

        parameters = parameters or "no parameter changes"
        logger.info("[%s] Simulating with %s", pool.symbol, parameters)

        pool.prepare_for_run(reference_market)

        for timestep in clock:
            pool.prepare_for_trades(timestep)
            sample = self._get_reference_sample(timestep)
            trader_args = self._get_trader_inputs(sample)
            trade_data = trader.process_time_sample(*trader_args)
            log.update(price_sample=sample, trade_data=trade_data)

        return log.compute_metrics()

    @abstractmethod
    def _get_trader_inputs(self, sample):
        """
        Process the price sample into appropriate inputs for the
        trader instance.
        """
        raise NotImplementedError

    @abstractmethod
    def _get_reference_sample(self, timestep):
        prices = []
        for asset in sim_assets:
            price = reference_market.price(asset, timestep)
            prices.append(price)
        return prices


def run_pipeline(configured_pools, price_sampler, executor, ncpu=4):
    """
    Core function for running pipelines.

    Typically called within a function specifying the pipeline components
    (see, e.g., :func:`curvesim.pipelines.vol_limited_arb.pipeline`)

    Parameters
    ----------
    configured_pools : iterator
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
            executor_args_list = [
                (sim_pool, price_sampler) for sim_pool in configured_pools
            ]

            wrapped_args_list = [
                (executor, logging_queue, *args) for args in executor_args_list
            ]

            with cpu_pool(ncpu) as clust:
                results = tuple(
                    zip(*clust.starmap(wrapped_executor, wrapped_args_list))
                )
                clust.close()
                clust.join()  # coverage needs this

    else:
        results = []
        for sim_pool in configured_pools:
            metrics = executor(sim_pool, price_sampler)
            results.append(metrics)
        results = tuple(zip(*results))

    return results


def wrapped_executor(executor, logging_queue, *args):
    """
    This wrapper ensures we configure logging to use the
    multiprocessing enqueueing logic within the new process.

    Must be defined at the top-level of the module so it can
    be pickled.
    """
    configure_multiprocess_logging(logging_queue)
    return executor(*args)


def configured_pool_sequence(sim_pool_factory, pool_metadata, variable_params):
    parameter_sequence = make_parameter_sequence(variable_params)
    for parameters in parameter_sequence:
        sim_pool = sim_pool_factory(pool_metadata, parameters)
        yield sim_pool
