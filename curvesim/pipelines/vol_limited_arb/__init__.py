"""
Implements the volume-limited arbitrage pipeline.
"""

import os

from curvesim.iterators.param_samplers import Grid
from curvesim.iterators.price_samplers import PriceVolume
from curvesim.logging import get_logger
from curvesim.metrics import init_metrics, make_results
from curvesim.metrics import metrics as Metrics
from curvesim.pool import get_sim_pool
from curvesim.pool_data.cache import PoolDataCache

from .. import run_pipeline
from ..utils import compute_volume_multipliers
from .strategy import VolumeLimitedStrategy

logger = get_logger(__name__)


# pylint: disable-next=too-many-arguments
def pipeline(
    pool_metadata,
    pool_data_cache=None,
    variable_params=None,
    fixed_params=None,
    metrics=None,
    test=False,
    days=60,
    src="coingecko",
    data_dir="data",
    vol_mult=None,
    vol_mode=1,
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

    test : bool, optional
        Overrides variable_params to use four test values:

        .. code-block::

            {"A": [100, 1000], "fee": [3000000, 4000000]}

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


    vol_mode : int, default=1
        Modes for limiting trade volume.

        1: limits trade volumes proportionally to market volume for each pair

        2: limits trade volumes equally across pairs

        3: mode 2 for trades with meta-pool asset, mode 1 for basepool-only trades

    ncpu : int, default=os.cpu_count()
        Number of cores to use.

    Returns
    -------
    SimResults object

    """
    if test:
        variable_params = TEST_PARAMS

    if ncpu is None:
        cpu_count = os.cpu_count()
        ncpu = cpu_count if cpu_count is not None else 1

    variable_params = variable_params or DEFAULT_PARAMS
    metrics = metrics or DEFAULT_METRICS

    if pool_data_cache is None:
        pool_data_cache = PoolDataCache(pool_metadata, days=days, end=end)

    pool = get_sim_pool(pool_metadata, pool_data_cache=pool_data_cache)

    param_sampler = Grid(pool, variable_params, fixed_params=fixed_params)
    price_sampler = PriceVolume(
        pool.assets, days=days, data_dir=data_dir, src=src, end=end
    )

    if vol_mult is None:
        total_pool_volume = pool_data_cache.volume
        total_market_volume = price_sampler.total_volumes()
        vol_mult = compute_volume_multipliers(
            total_pool_volume,
            total_market_volume,
            pool_metadata.n,
            pool_metadata.pool_type,
            mode=vol_mode,
        )

    metrics = init_metrics(metrics, pool=pool)
    strategy = VolumeLimitedStrategy(metrics, vol_mult)

    output = run_pipeline(param_sampler, price_sampler, strategy, ncpu=ncpu)
    results = make_results(*output, metrics)

    return results


# Defaults
DEFAULT_METRICS = [
    Metrics.Timestamp,
    Metrics.PoolValue,
    Metrics.PoolBalance,
    Metrics.PriceDepth,
    Metrics.PoolVolume,
    Metrics.ArbMetrics,
]

DEFAULT_PARAMS = {
    "A": [int(2 ** (a / 2)) for a in range(12, 28)],
    "fee": list(range(1000000, 5000000, 1000000)),
}

TEST_PARAMS = {"A": [100, 1000], "fee": [3000000, 4000000]}
