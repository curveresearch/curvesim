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
from abc import ABC, abstractmethod
from collections.abc import Iterator
from multiprocessing import Pool as cpu_pool
from typing import Callable, Dict, List, Type

from curvesim.iterators.param_samplers.parameterized_pool_iterator import (
    ParameterizedPoolIterator,
)
from curvesim.iterators.price_samplers.price_volume import PriceVolume
from curvesim.logging import (
    configure_multiprocess_logging,
    get_logger,
    multiprocessing_logging_queue,
)
from curvesim.metrics import init_metrics
from curvesim.metrics.base import Metric
from curvesim.metrics.results import make_results
from curvesim.metrics.state_log.log import StateLog
from curvesim.pipelines.common import DEFAULT_METRICS
from curvesim.pipelines.vol_limited_arb.trader import VolumeLimitedArbitrageur
from curvesim.pool import get_sim_pool
from curvesim.pool_data.metadata.base import PoolMetaDataInterface
from curvesim.templates.log import Log
from curvesim.templates.trader import Trader
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


class FileSource:
    """
    Loads a given csv or json file containing
    market data.
    """

    def __init__(self, filepath):
        ...


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


@dataclass
class SimMarketParameters:
    initial_parameters: Dict
    run_parameters: List[Dict]


@dataclass
class RunConfig(ABC):
    sim_assets: List[SimAsset]
    clock: Clock
    data_sources: List[DataSource]
    asset_to_source: Dict[SimAsset, DataSource]
    sim_market_parameters


class AutoConfig(RunConfig):
    """
    Convenience class to autogenerate the SimAssets from Curve pool metadata.
    """

    def __init__(self, pool_metadata, source_config):
        self._pool_metadata = pool_metadata


@dataclass
class StrategyConfig(ABC):
    sim_market_factory: Callable
    reference_market_factory: Type[ReferenceMarket]
    trader_class: Type[Trader]
    log_class: Type[Log]
    metrics: List[Metric]


class VolumeLimitedArbitrageConfig(StrategyConfig):
    sim_market_factory = get_sim_pool
    reference_market_factory = SingleSourceReferenceMarket
    trader_class = VolumeLimitedArbitrageur
    log_class = StateLog
    metrics = DEFAULT_METRICS


class Simulation:
    pass


class VolumeLimitedArbitrage(Simulation, VolumeLimitedArbitrageConfig, AutoConfig):
    def run(self, variable_params, fixed_params, ncpu=4):
        # strategy config
        metrics = self.metrics
        sim_market_factory = self.sim_market_factory
        # run config
        sim_assets = self.sim_assets
        clock = self.clock
        data_source = self.data_sources[0]

        reference_market = self.reference_market_factory(sim_assets, data_source, clock)
        configured_markets = configured_market_sequence(
            sim_market_factory, sim_market_args, fixed_params, variable_params
        )

        executor = self.execute_run

        output = run_pipeline(configured_markets, reference_market, executor, ncpu)

        data_per_run, data_per_trade, summary_data = output
        self.run_outputs.append(output)

        results = make_results(*output, metrics)
        self.results.append(results)

    def execute_run(self, pool, parameters, reference_market, clock):
        trader = self.trader_class(pool)
        metrics = init_metrics(self.metrics, pool=pool)
        log = self.log_class(pool, metrics)

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


def run_pipeline(configured_markets, price_sampler, executor, ncpu=4):
    """
    Core function for running pipelines.

    Typically called within a function specifying the pipeline components
    (see, e.g., :func:`curvesim.pipelines.vol_limited_arb.pipeline`)

    Parameters
    ----------
    configured_markets : iterator
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
                (sim_pool, price_sampler) for sim_pool in configured_markets
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
        for sim_pool in configured_markets:
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


def configured_market_sequence(
    sim_market_factory,
    sim_market_args,
    fixed_params,
    variable_params,
):
    parameter_sequence = make_parameter_sequence(variable_params)
    for parameters in parameter_sequence:
        custom_kwargs = fixed_params.copy()
        custom_kwargs.update(parameters)
        sim_pool = sim_market_factory(sim_market_args, custom_kwargs)
        yield sim_pool
