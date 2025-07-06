"""
Implements the volume-limited arbitrage pipeline.
"""

import os

from curvesim.iterators.param_samplers import ParameterizedPoolIterator
from curvesim.iterators.price_samplers import PriceVolume
from curvesim.logging import get_logger
from curvesim.metrics import init_metrics, make_results
from curvesim.pool_data import get_pool_volume

from .. import run_pipeline
from ..common import DEFAULT_METRICS, get_asset_data, get_pool_data
from .strategy import VolumeLimitedStrategy

logger = get_logger(__name__)


# pylint: disable-next=too-many-locals
def pipeline(
    metadata_or_address,
    *,
    chain="mainnet",
    variable_params=None,
    fixed_params=None,
    metrics=None,
    src="coingecko",
    time_sequence=None,
    vol_mult=None,
    pool_ts=None,
    ncpu=None,
    env="prod",
):
    """
    Implements the volume-limited arbitrage pipeline.

    At each timestep, the pool is arbitraged as close to the prevailing market price
    as possible without surpassing a volume constraint. By default, volume is limited
    to the total market volume at each timestep, scaled by the proportion of
    volume attributable to the pool over the whole simulation period (vol_mult).

    Parameters
    ----------
    metadata_or_address: :class:`~curvesim.pool_data.metadata.PoolMetaDataInterface` or str
        Pool metadata obect or address to fetch metadata for.

    chain : str or :class:`curvesim.constants.Chain`, default="mainnet"
        Chain to use if fetching metadata by address.

    variable_params : dict
        Pool parameters to vary across simulations.
        keys: pool parameters, values: iterables of ints

        Example
        --------
        >>> variable_params = {"A": [100, 1000], "fee": [10**6, 4*10**6]}

    fixed_params : dict, optional
        Pool parameters set before all simulations.
        keys: pool parameters, values: ints

        Example
        --------
        >>> fixed_params = {"D": 1000000*10**18}

    metrics : list of :class:`~curvesim.metrics.base.Metric` classes, optional
        Metrics to compute for each simulation run.
        Defaults to `curvesim.pipelines.common.DEFAULT_METRICS`

    src : str or :class:`~curvesim.templates.DateSource`, default="coingecko"
        Source for price/volume data: "coingecko" or "local".

    time_sequence : :class:`~curvesim.templates.DateTimeSequence`, optional
        Timepoints for price/volume data and simulated trades.

    vol_mult : dict, default computed from data
        Value(s) multiplied by market volume to specify volume limits
        (overrides vol_mode).

        dict should map from trade-pair tuples to values, e.g.:

        .. code-block::

            {('DAI', 'USDC'): 0.1, ('DAI', 'USDT'): 0.1, ('USDC', 'USDT'): 0.1}

    pool_ts : datetime.datetime or int, optional
        Optional timestamp to use when fetching metadata by address.

    ncpu : int, default=os.cpu_count()
        Number of cores to use.

    Returns
    -------
    SimResults object
    """
    if ncpu is None:
        cpu_count = os.cpu_count()
        ncpu = cpu_count if cpu_count is not None else 1

    pool, pool_metadata = get_pool_data(metadata_or_address, chain, env, pool_ts)
    asset_data, time_sequence = get_asset_data(pool_metadata, time_sequence, src)
    asset_data = asset_data.dropna()

    # pylint: disable-next=abstract-class-instantiated
    param_sampler = ParameterizedPoolIterator(pool, variable_params, fixed_params)
    price_sampler = PriceVolume(asset_data)

    if vol_mult is None:
        pool_volume = get_pool_volume(pool_metadata, time_sequence[0], time_sequence[-1])
        vol_mult = pool_volume.sum() / price_sampler.volumes.sum()
        logger.info("Volume Multipliers:\n%s", vol_mult.to_string())
        vol_mult = vol_mult.to_dict()

    metrics = metrics or DEFAULT_METRICS
    metrics = init_metrics(metrics, pool=pool)
    strategy = VolumeLimitedStrategy(metrics, vol_mult)

    output = run_pipeline(param_sampler, price_sampler, strategy, ncpu=ncpu)
    results = make_results(*output, metrics)

    return results
