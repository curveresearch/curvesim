"""
Implements the volume-limited arbitrage pipeline.
"""

import os

from curvesim.iterators.param_samplers import ParameterizedPoolIterator
from curvesim.iterators.price_samplers import PriceVolume
from curvesim.logging import get_logger
from curvesim.metrics import init_metrics, make_results
from curvesim.pool import get_sim_pool
from curvesim.pool_data import get_pool_volume

from .. import run_pipeline
from ..common import DEFAULT_METRICS
from .strategy import VolumeLimitedStrategy

logger = get_logger(__name__)


# pylint: disable-next=too-many-locals
def pipeline(
    pool_metadata,
    *,
    variable_params=None,
    fixed_params=None,
    metrics=None,
    days=60,
    src="coingecko",
    data_dir="data",
    vol_mult=None,
    ncpu=None,
    end=None,
):
    """
    Implements the volume-limited arbitrage pipeline.

    At each timestep, the pool is arbitraged as close to the prevailing market price
    as possible without surpassing a volume constraint. By default, volume is limited
    to the total market volume at each timestep, scaled by the proportion of
    volume attributable to the pool over the whole simulation period (vol_mult).

    Parameters
    ----------
    pool_metadata : :class:`~curvesim.pool_data.metadata.PoolMetaDataInterface`
        Pool metadata object for the pool of interest.

    variable_params : dict, defaults to broad range of A/fee values
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

    days : int, default=60
        Number of days to pull pool and price data for.

    src : str, default="coingecko"
        Source for price/volume data: "coingecko" or "local".

    data_dir : str, default="data"
        relative path to saved price data folder

    vol_mult : dict, default computed from data
        Value(s) multiplied by market volume to specify volume limits
        (overrides vol_mode).

        dict should map from trade-pair tuples to values, e.g.:

        .. code-block::

            {('DAI', 'USDC'): 0.1, ('DAI', 'USDT'): 0.1, ('USDC', 'USDT'): 0.1}

    ncpu : int, default=os.cpu_count()
        Number of cores to use.

    Returns
    -------
    SimResults object
    """
    if ncpu is None:
        cpu_count = os.cpu_count()
        ncpu = cpu_count if cpu_count is not None else 1

    pool = get_sim_pool(pool_metadata)

    # pylint: disable-next=abstract-class-instantiated
    param_sampler = ParameterizedPoolIterator(pool, variable_params, fixed_params)
    price_sampler = PriceVolume(
        pool.assets, days=days, data_dir=data_dir, src=src, end=end
    )

    if vol_mult is None:
        pool_volume = get_pool_volume(pool_metadata, days=days, end=end)
        vol_mult = pool_volume.sum() / price_sampler.volumes.sum()
        logger.info("Volume Multipliers:\n%s", vol_mult.to_string())
        vol_mult = vol_mult.to_dict()

    metrics = metrics or DEFAULT_METRICS
    metrics = init_metrics(metrics, pool=pool)
    strategy = VolumeLimitedStrategy(metrics, vol_mult)

    output = run_pipeline(param_sampler, price_sampler, strategy, ncpu=ncpu)
    results = make_results(*output, metrics)

    return results
