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
from typing import Any, Callable, Dict, List, Type

from curvesim.constants import Chain
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


class TimeSequence(Iterator):
    """
    Time-like sequence generator.

    Abstraction to encompass different ways of tracking "time",
    useful for trading strategies involving a blockchain.
    This could be timestamps, block times, block numbers, etc.
    """

    @abstractmethod
    def __iter__(self):
        raise NotImplementedError

    @abstractmethod
    def __getitem__(self, index):
        raise NotImplementedError


@dataclass(frozen=True)
class TimestampPeriod(TimeSequence):
    start: int
    end: int
    freq: str


class DataSource(ABC):
    """
    Typically, there is a sole data source that aggregates
    data from a single data provider such as Coingecko or Kaiko.

    However, this abstraction lets us use multiple sources or
    easily swap one for another.

    A data source may have an underlying API or be as simple
    as a flat file.
    """

    @abstractmethod
    def query(self, params) -> Any:
        raise NotImplementedError


class SimAsset:
    id: str


class SimAssetSeries(ABC):
    """
    Pandas Series-like abstraction for a SimAsset's market data.

    The most common indexing and slicing operations should be supported,
    but it is important to allowed operations should be fairly limited
    to reduce complexity of dependent code.
    """

    sim_asset: SimAsset


class SimAssetSeriesFactory(ABC):
    """
    Factory to product an SimAssetSeries from its main components.

    Specific creation strategies for data sourcing/loading
    can be handled by subclassing this factory and choosing
    custom data sources.

    DataSource can be per SimAssetSeries (or as a override/overlay)
    with the "main" one being added at initialization of the factory.
    """

    def create(
        self,
        sim_asset: SimAsset,
        time_sequence: TimeSequence,
        data_source: DataSource = None,
    ) -> SimAssetSeries:
        raise NotImplementedError


@dataclass
class CurrencyPair(SimAsset):
    base_symbol: str
    quote_symbol: str


@dataclass
class PoolPair(CurrencyPair):
    chain: Chain
    pool_address: str
    base_coin_address: str
    quote_coin_address: str


class ReferenceMarket(ABC):
    @abstractmethod
    def price(self, sim_asset: SimAsset, timestep):
        """
        This signature supposes:
        - an infinite-depth external venue, i.e. we can trade at any size
          at the given price without market impact.
        - the "orderbook" is symmetric, i.e. trade direction doesn't matter.
        """
        raise NotImplementedError


class ReferenceMarketFactory(ABC):
    def create(
        self,
        sim_asset_series: List[SimAssetSeries],
        *args,
        **kwargs,
    ) -> ReferenceMarket:
        raise NotImplementedError


@dataclass
class SimMarketParameters:
    initial_parameters: Dict
    run_parameters: List[Dict]


class SimMarketFactory:
    @abstractmethod
    def create(self, **init_kwargs):
        raise NotImplementedError


@dataclass
class RunConfig(ABC):
    time_sequence: TimeSequence
    sim_asset_series: List[SimAssetSeries]
    sim_market_parameters: SimMarketParameters


class SimPoolAutoConfig(RunConfig):
    """
    Convenience class to autogenerate the SimAssets from Curve pool metadata
    and create appropriate SimAssetSeries based on some config file.
    """

    def __init__(self, pool_metadata, data_config_file):
        self._pool_metadata = pool_metadata

    @property
    def sim_assets(self):
        ...

    @property
    def sim_asset_series(self):
        ...


class Simulation:

    # inject using Gin:
    # (can use AutoConfig)
    run_config: RunConfig

    reference_market_factory: Type[ReferenceMarketFactory]
    sim_market_factory: Type[SimMarketFactory]
    trader_class: Type[Trader]
    log_class: Type[Log]
    metrics: List[Metric]
    # Gin injection config for volume-limited arbitrage
    #
    # sim_market_factory = get_sim_pool
    # reference_market_factory = ReferenceMarketFactory
    # trader_class = VolumeLimitedArbitrageur
    # log_class = StateLog
    # metrics = DEFAULT_METRICS

    run_outputs: List
    results: List

    @property
    def sim_assets(self):
        return self.run_config.sim_assets

    @property
    def sim_asset_series(self):
        return self.run_config.sim_asset_series

    @property
    def time_sequence(self):
        return self.run_config.time_sequence

    @property
    def sim_market_parameters(self):
        return self.run_config.sim_market_parameters

    def __init__(self, *args, **kwargs):
        sim_asset_series = self.sim_asset_series
        time_sequence = self.time_sequence

        self.reference_market = self.reference_market_factory(
            sim_asset_series, time_sequence
        )

    def configured_market_sequence(self):
        sim_market_parameters = self.sim_market_parameters
        initial_params = sim_market_parameters.initial_parameters

        for run_params in sim_market_parameters.run_parameters:
            init_kwargs = initial_params.copy()
            init_kwargs.update(run_params)
            sim_market = self.sim_market_factory.create(**init_kwargs)
            yield sim_market, run_params

    def run(self, variable_params, fixed_params, ncpu=4):

        configured_markets = self.configured_market_sequence()
        executor = self.execute_run
        reference_market = self.reference_market

        output = run_pipeline(configured_markets, reference_market, executor, ncpu)
        self.run_outputs.append(output)

        metrics = self.metrics
        results = make_results(*output, metrics)
        self.results.append(results)

    def execute_run(self, sim_market, reference_market):
        trader = self.trader_class(sim_market)
        metrics = init_metrics(self.metrics, pool=sim_market)
        log = self.log_class(sim_market, metrics)

        parameters = parameters or "no parameter changes"
        logger.info("[%s] Simulating with %s", pool.symbol, parameters)

        sim_market.prepare_for_run(reference_market)

        for timestep in self.time_sequence:
            sim_market.prepare_for_trades(timestep)
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
        for asset in self.sim_assets:
            price = self.reference_market.price(asset, timestep)
            prices.append(price)
        return prices


def run_pipeline(sim_markets, reference_market, executor, ncpu=4):
    """
    Core function for running pipelines.

    Typically called within a function specifying the pipeline components
    (see, e.g., :func:`curvesim.pipelines.vol_limited_arb.pipeline`)

    Parameters
    ----------
    sim_markets : iterator
        An iterator that yields a configured SimMarket

    price_sampler : iterator
        An iterator that returns (minimally) a time-series of prices
        (see :mod:`.price_samplers`).

    executor: callable
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
                (sim_market, reference_market) for sim_market in sim_markets
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
        for sim_market in sim_markets:
            metrics = executor(sim_market, reference_market)
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
