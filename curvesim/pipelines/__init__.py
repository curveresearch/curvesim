"""
Tools for implementing and running simulation pipelines.


# inside Gin config
# config.py

sim_market_parameters = {
    initial_parameters = {

    },
    run_parameters = {

    },
}
Simulation.configured_market_sequence.sim_market_parameters = sim_market_parameters


from curvesim.pipelines.common import DEFAULT_METRICS
Simulation.init_metrics.metrics = DEFAULT_METRICS

"""
import os
from abc import ABC, abstractmethod
from collections.abc import Iterator
from multiprocessing import Pool as cpu_pool
from typing import Any, Callable, Dict, List, Type

import gin

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
    def price(self, sim_asset: SimAsset, timestep) -> float:
        """
        This signature supposes:
        - an infinite-depth external venue, i.e. we can trade at any size
          at the given price without market impact.
        - the "orderbook" is symmetric, i.e. trade direction doesn't matter.
        """
        raise NotImplementedError

    @abstractmethod
    def prices(self, sim_assets: List[SimAsset], timestep) -> List[float]:
        """Same as `price` but retrieves prices for multiple assets in one call."""
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


@gin.configurable
class Simulation:

    sim_assets: List[SimAsset]
    sim_assets_series: List[SimAssetSeries]

    time_sequence: TimeSequence

    reference_market_factory: Type[ReferenceMarketFactory]
    sim_market_factory: Type[SimMarketFactory]
    trader_factory: Type[Trader]
    log_factory: Type[Log]
    metrics: List[Metric]
    # Gin injection config for volume-limited arbitrage
    #
    # sim_market_factory = get_sim_pool
    # reference_market_factory = ReferenceMarketFactory
    # trader_factory = VolumeLimitedArbitrageur
    # log_factory = StateLog
    # metrics = DEFAULT_METRICS

    run_outputs: List
    results: List


@gin.register
def configured_sim_markets(self, sim_market_factory, sim_market_parameters):
    sim_market_parameters = sim_market_parameters
    initial_params = sim_market_parameters.initial_parameters
    all_run_params = sim_market_parameters.run_parameters

    for run_params in all_run_params:
        init_kwargs = initial_params.copy()
        init_kwargs.update(run_params)
        sim_market = sim_market_factory.create(**init_kwargs)
        yield sim_market


@gin.register
def init_metrics(metric_classes, sim_market):
    return [Metric(pool=sim_market) for Metric in metric_classes]


@gin.register
def run_simulation(
    initial_parameters,
    run_parameters,
    executor,
    reference_market,
    configured_sim_markets,
    ncpu=None,
):
    output = run_pipeline(configured_sim_markets, reference_market, executor, ncpu)
    metrics = init_metrics(sim_market)
    results = make_results(*output, metrics)
    return results


def execute_run(
    time_sequence,
    sim_market,
    reference_market,
    trader_factory,
    log_factory,
):
    trader = trader_factory(sim_market)
    log = log_factory(sim_market)

    sim_market.prepare_for_run(reference_market)

    for timestep in time_sequence:
        sim_market.prepare_for_trades(timestep)
        sample = reference_market.prices(timestep)
        trade_data = trader.process_time_sample(sample)
        log.update(price_sample=sample, trade_data=trade_data)

    return log.compute_metrics()


def run_pipeline(sim_markets, reference_market, executor, ncpu=None):
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

    ncpu : int, optional
        Number of cores to use.  Defaults to number of available cores.

    Returns
    -------
    results : tuple
        Contains the metrics produced by the strategy.

    """
    if ncpu is None:
        cpu_count = os.cpu_count()
        ncpu = cpu_count if cpu_count is not None else 1

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
