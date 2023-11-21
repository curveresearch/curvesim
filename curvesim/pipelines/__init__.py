"""
Tools for implementing and running simulation pipelines.
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
    # TODO: add generation of unix timestamps


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
    Factory to produce a SimAssetSeries from its main components.

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


@gin.register
class ReferenceMarket(ABC):
    @gin.register
    @abstractmethod
    def prices(self, sim_assets: List[SimAsset], timestep) -> List[float]:
        """
        Retrieves prices for multiple assets in one call.

        This signature supposes:
        - an infinite-depth external venue, i.e. we can trade at any size
          at the given price without market impact.
        - the "orderbook" is symmetric, i.e. trade direction doesn't matter.
        """
        raise NotImplementedError


@gin.register
class ReferenceMarketFactory(ABC):
    @gin.register
    @abstractmethod
    def create(
        self,
        sim_asset_series_list: List[SimAssetSeries],
        *args,
        **kwargs,
    ) -> ReferenceMarket:
        raise NotImplementedError


@gin.register
class SimMarketFactory:
    @abstractmethod
    def create(self, **init_kwargs):
        raise NotImplementedError


@gin.configurable
class SimulationContext:
    """
    Basically an 'IoC' container for the simulation application.

    While Gin doesn't require such a container object, this makes configuration
    more explicit.
    """

    # all constructor args will be Gin injected
    def __init__(
        self,
        time_sequence,
        reference_market,
        sim_market_factory,
        sim_market_parameters,
        trader_class,
        log_class,
        metric_classes,
    ):
        self.time_sequence = time_sequence
        self.reference_market = reference_market
        self.sim_market_factory = sim_market_factory
        self.sim_market_parameters = sim_market_parameters
        self.trader_class = trader_class
        self.log_class = log_class
        self.metric_classes = metric_classes

    def executor(
        self,
        sim_market,
    ):
        """
        Executes a trading strategy for the given sim market
        and time sequence.
        """
        # These all use Gin injection, completely separating
        # any need to consider constructor dependencies from
        # this logic.
        trader = self.trader_class()
        log = self.log_class()
        sim_market.prepare_for_run()

        for timestep in self.time_sequence:
            sim_market.prepare_for_trades(timestep)
            sample = self.reference_market.prices(timestep)
            trade_data = trader.process_time_sample(sample, sim_market)
            log.update(price_sample=sample, trade_data=trade_data)

        return log.compute_metrics()

    @property
    def configured_sim_markets(
        self,
    ):
        sim_market_parameters = self.sim_market_parameters
        sim_market_factory = self.sim_market_factory

        initial_params = sim_market_parameters.initial_parameters
        all_run_params = sim_market_parameters.run_parameters

        yield sim_market_factory.create(**initial_params)

        for run_params in all_run_params:
            init_kwargs = initial_params.copy()
            init_kwargs.update(run_params)
            sim_market = sim_market_factory.create(**init_kwargs)
            yield sim_market

    def run_simulation(
        self,
        ncpu=None,
    ):
        configured_sim_markets = self.configured_sim_markets
        initial_sim_market = next(configured_sim_markets)
        output = run_pipeline(configured_sim_markets, self.executor, ncpu)

        metrics = [Metric(pool=initial_sim_market) for Metric in self.metric_classes]
        results = make_results(*output, metrics)
        return results


def run_pipeline(sim_markets, executor, ncpu=None):
    """
    Core function for running pipelines.

    Parameters
    ----------
    sim_markets : iterator
        An iterator that yields a configured SimMarket

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
            # XXX: probably need to augment the args
            executor_args_list = [sim_market for sim_market in sim_markets]

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
            metrics = executor(sim_market)
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


if __name__ == "__main__":
    gin.parse_config_file("config.gin")
    sim_context = SimulationContext()
    sim_context.run_simulation()
