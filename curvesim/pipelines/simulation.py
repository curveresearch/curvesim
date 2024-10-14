import os
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any, Union, Tuple, List

import gin

from pandas import concat

from curvesim.metrics import SimResults, make_results, init_metrics
from curvesim.pipelines import run_pipeline
from curvesim.pipelines.common import get_asset_data
from curvesim.iterators.price_samplers import PriceVolume
from curvesim.templates import SimPool, TimeSequence, DateTimeSequence
from curvesim.pool import get_sim_pool
from curvesim.pool_data import get_metadata, get_pool_volume
from curvesim.pool_data.metadata import PoolMetaData, PoolMetaDataInterface
#from curvesim.pool_data.metadata.sim_market_config import SimMarketConfig
from curvesim.utils import is_address
from curvesim.constants import CurvePreset
from curvesim.logging import get_logger

from curvesim.iterators.param_samplers import ParameterizedPoolIterator

from curvesim.pipelines.simple.trader import SimpleArbitrageur # import these two from common module
from curvesim.pipelines.vol_limited_arb.trader import VolumeLimitedArbitrageur # remove import of this from vol_limited_arb.__init__
from curvesim.metrics.state_log import StateLog


logger = get_logger(__name__)


@gin.configurable
class SimulationContext:
    """
    An Inversion-of-Control (IoC) container for the simulation application
    that uses Gin for dependency injection.

    While Gin doesn't require such a container, this makes configuration
    more explicit.

    Example usage
    -------------
    >>> import gin
    >>> gin.parse_config_file("config.gin")
    >>> sim_context = SimulationContext()
    >>> sim_context.run_simulation()
    """

    def __init__(
        self,
        time_sequence,
        #data_source,
        # reference_market,
        # sim_market_factory,
        # sim_market_parameters,
        trader_class,
        log_class,
        metric_classes,
        simulation_runs,
        #vol_mult,
    ):
        """
        all constructor args will be Gin injected
        """
        # self.time_sequence = time_sequence
        # self.reference_market = reference_market
        # self.sim_market_factory = sim_market_factory
        # self.sim_market_parameters = sim_market_parameters
        self.time_sequence = eval(time_sequence) if time_sequence else make_default_time_sequence() # force/allow list instead?
        #self.time_sequence = make_default_time_sequence()
        # pass in string name of trader/log class and this instantiates here
        self.trader_class = eval(trader_class)
        self.log_class = eval(log_class)
        self.metric_classes = metric_classes # eval?

        # need data source param
        self.data_source = "coingecko" # force/allow list like for time_sequence?
        # only support coingecko for now? local needs some cleaning up
        # curve prices ApiDataSource class?

        # where to store the meta types per run?

        # experimental
        #assert isinstance(simulation_runs, dict)
        self.simulation_runs = simulation_runs

        # TODO: make time_sequence always a list?
        # time_sequence = eval(time_sequence) if time_sequence else make_default_time_sequence()
        # if isinstance(time_sequence, TimeSequence):
        #     self.time_sequence = time_sequence
        # elif isinstance(time_sequence, list) and all([isinstance(ts, TimeSequence) for ts in time_sequence]):
        #     if len(time_sequence) == len(self.simulation_runs.keys()):
        #         self.time_sequence = time_sequence
        #     else:
        #         raise ValueError
        # else:
        #     raise TypeError

        # data_source = eval(data_source) if data_source else "coingecko"
        # if isinstance(data_source, str):
        #     self.data_source = data_source
        # elif isinstance(data_source, list) and all([isinstance(src, str) for src in data_source]):
        #     if len(data_source) == len(self.simulation_runs.keys()):
        #         self.data_source = data_source
        #     else:
        #         raise ValueError
        # else:
        #     raise TypeError
        

        # what's next for our api needs? discuss with Naga
        # use curve prices api instead of subgraph for snapshot (get_pool_data)


        # NOT RECOMMENDED TO CONFIGURE
        # ----------------------------
        self.vol_mult = None


    def _get_trader_inputs(self, sample) -> Tuple:
        """
        Process the price sample into appropriate inputs for the
        trader instance.

        Parameters

        Returns

        Raises
        """
        if self.trader_class is SimpleArbitrageur:
            return (sample.prices)
        elif self.trader_class is VolumeLimitedArbitrageur:
            prices = sample.prices
            volumes = sample.volumes
            vol_mult = self.vol_mult

            volume_limits = {key: volumes[key] * vol_mult[key] for key in volumes}
            reversed_limits = {(j, i): lim * prices[(i, j)] for (i, j), lim in volume_limits.items()}
            all_limits = {**volume_limits, **reversed_limits}
            normalized_vol_limits = {key: int(val * 10**18) for key, val in all_limits.items()}

            return (prices, normalized_vol_limits)
        else:
            pass
            #raise CurvesimTypeError("TODO") # TODO


    def executor(self, sim_market, parameters, price_volume, metrics):
        """
        Executes a trading strategy for the given sim market
        and time sequence.

        Returns
        -------

        tuple of dataframes
        """
        # These all use Gin injection, completely separating
        # any need to consider constructor dependencies from
        # this logic.

        # applied once per run - referencemarket and timesequence are supposed to be agnostic of trading strategy (eg volume-limited)
        trader = self.trader_class()
        log = self.log_class(sim_market) # needs pool and metrics, but maybe remove pool (at minimum) later

        # (if have multiple pools in one sim)
        # every run, you probably only care about the metrics recorded on one pool (in multipool run, why assume a trader will route their trades through the specific pools loaded?)

        parameter_changes = str(parameters) if parameters else "no parameter changes"
        logger.info("[%s] Simulating with %s", sim_market.symbol, parameter_changes)

        sim_market.prepare_for_run(price_volume.prices) # needs pricesampler.prices (DF)

        price_sampler = iter(price_volume)

        for timestep in self.time_sequence:
            sim_market.prepare_for_trades(timestep) # move pool timestamp
            #sample = self.reference_market.prices(timestep) # TODO: ReferenceMarket (wrapper around PriceVolume)
            # we assume that the PriceVolume object's timestamps have been aligned with that of self.time_sequence
            price_volume_sample = next(price_sampler) # iterate over PriceVolume obj itself above? (for now)
            # use price_sampler timestamp index or not? or price sample timestamp? above works only if timesequence and sampler timestamps align

            trader_args = self._get_trader_inputs(price_volume_sample)

            #trade_data = trader.process_time_sample(sample, sim_market) # this is computing trades with prices at current timestamp
            trade_data = trader.process_time_sample(sim_market, *trader_args)
            
            # update after
            log.update(
                pool=sim_market,
                price_sample=price_volume_sample,
                trade_data=trade_data,
                #sim_market=sim_market,
            )

        run_logs = log.get_logs()

        return compute_metrics(run_logs, metrics) # change later


    @property
    def configured_sim_markets(self): # rename configured_sim_runs?
        #sim_market_factory = self.sim_market_factory

        for sim_name, sim_info_dict in self.simulation_runs.items():
            # for now, only one market per run will be supported
            for sim_market_config in sim_info_dict["markets"]:

                pool = config_to_sim_market(sim_market_config)
                variable_params = deepcopy(sim_market_config.overrides)
                metadata_template = config_to_metadata(sim_market_config)

                if sim_market_config.include_template:
                    #metadata_template = config_to_metadata(sim_market_config)
                    template_params = metadata_template.init_kwargs()

                    for param_name, value_list in variable_params.items():
                        include = template_params[param_name] # only template params that have corresponding overrides need to be included in variable_params
                        new_list = [include] + value_list
                        variable_params[param_name] = new_list

                vol_mult = sim_info_dict["vol_mult"]   

                yield (ParameterizedPoolIterator(pool, variable_params=variable_params), metadata_template, vol_mult)
                # [yield ParameterizedPoolIterator for each simmarket in this sim]
                # for multiple, create empty list in loop above and append pools and then yield at end of loop above?


    def run_simulation(self, ncpu=None) -> List[SimResults]:
        """
        Parameters
        ----------
        ncpu : int, optional
            Number of cores to use.  Defaults to `os.cpu_count()`.
            Use `ncpu==1` for profiling or debugging.

        Returns
        -------
        results : SimResults
            Contains the metrics produced by the strategy.

        """
        if ncpu is None:
            cpu_count = os.cpu_count()
            ncpu = cpu_count if cpu_count is not None else 1

        every_result: List[SimResults] = []

        sim_counter = 0

        for configured_sim_markets, sim_market_metadata, vol_mult in self.configured_sim_markets:
            template_sim_market = configured_sim_markets.pool_template

            metrics = init_metrics(self.metric_classes, pool=template_sim_market)

            # TODO: make time_sequence always a list?
            if isinstance(self.time_sequence, list):
                time_sequence = self.time_sequence[sim_counter]
            else:
                time_sequence = self.time_sequence

            if isinstance(self.data_source, list):
                data_source = self.data_source[sim_counter]
            else:
                data_source = self.data_source

            asset_data, _ = get_asset_data(sim_market_metadata, time_sequence, data_source) 
            price_volume = PriceVolume(asset_data)

            if vol_mult is None:
                pool_volume = get_pool_volume(
                    sim_market_metadata, time_sequence[0], time_sequence[-1]
                )
                # TODO: mark these two as DataFrames properly
                vol_mult = pool_volume.sum() / price_volume.volumes.sum()
                logger.info("Volume Multipliers:\n%s", vol_mult.to_string())
                vol_mult = vol_mult.to_dict()

            self.vol_mult = vol_mult
            
            output = run_pipeline(configured_sim_markets, price_volume, self.executor, metrics, ncpu=ncpu)

            results = make_results(*output, metrics)
            every_result.append(results)

            logger.info("done lol") # TODO: one run finished, onto the next one - use name from simulation_runs?

            sim_counter += 1

        return every_result


@gin.register # unregister this?
def config_to_metadata(sim_market_config: SimMarketConfig) -> PoolMetaDataInterface:
    """
    returns default PoolMetaDataInterface (no override) based on key_metadata supplied for instantiation
    """
    metadata = sim_market_config.key_metadata

    if is_address(metadata): # TODO reflect simmarketconfig changes
        address = metadata
        chain = sim_market_config.chain
        end_ts = sim_market_config.end_ts
        metadata_interface = get_metadata(address, chain=chain, end_ts=end_ts)

    if isinstance(metadata, dict): # dict in "subgraph" style (actually a curvesim-defined format)
        if "preset" in metadata:
            metadata_dict = create_preset_metadata(metadata) # returns dict in our defined format
            metadata_interface = PoolMetaData(metadata_dict)
        else:
            metadata_interface = PoolMetaData(metadata)

    if isinstance(metadata, PoolMetaDataInterface):
        metadata_interface = metadata

    return metadata_interface


@gin.register # unregister this?
def config_to_sim_market(sim_market_config: SimMarketConfig) -> SimPool:
    """
    Factory function for simmarkets
    """
    metadata_interface = config_to_metadata(sim_market_config)
    chain = sim_market_config.chain
    balanced = sim_market_config.balanced
    balanced_base = sim_market_config.balanced_base
    end_ts = sim_market_config.end_ts

    sim_market = get_sim_pool(metadata_interface, chain=chain, balanced=balanced, balanced_base=balanced_base, end_ts=end_ts)

    return sim_market



def compute_metrics(state_logs, metrics) -> tuple:
    """
    Computes metrics from the accumulated log data.

    make sure state_logs and metrics._pool are referring to the same pool

    Parameters TODO: write
    ----------
    state_logs : dict 
    from statelog or just log 

    metrics : List[Metric]
    already initialized

    Returns
    -------

    tuple of dataframes
    """
    data_per_run = state_logs["pool_parameters"]
    metric_data = [metric.compute(state_logs) for metric in metrics]
    data_per_trade, summary_data = tuple(zip(*metric_data))  # transpose tuple list

    data_per_trade = concat(data_per_trade, axis=1)
    summary_data = concat(summary_data, axis=1)

    return (
        data_per_run,
        data_per_trade,
        summary_data,
    )


def make_default_time_sequence() -> DateTimeSequence:
    t_end = datetime.now(timezone.utc) - timedelta(days=1)
    t_end = t_end.replace(hour=23, minute=0, second=0, microsecond=0)
    t_start = t_end - timedelta(days=60) + timedelta(hours=1)
    time_sequence = DateTimeSequence.from_range(start=t_start, end=t_end, freq="1h")

    return time_sequence

# allow creation of PoolMetaDataBase child classes in .gin?
# helper function: simulation_runs_setting(# of pipelines)
# rigourously define (sim) run, pipeline, simulation, etc. for docs
# one day simulate param changes within a run?
# option to parallelize sims? (after reading all data necessary for all sims)
    # append info for each run to list in for loop, schedule coroutines?
# make pkg min required version 3.10