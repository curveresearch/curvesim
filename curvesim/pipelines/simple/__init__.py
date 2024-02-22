"""
Implements the simple arbitrage pipeline, a very simplified version of
:func:`curvesim.pipelines.vol_limited_arb.pipeline`.
"""

import os

from curvesim.iterators.param_samplers import ParameterizedPoolIterator
from curvesim.iterators.price_samplers import PriceVolume
from curvesim.metrics import init_metrics
from curvesim.metrics.results import make_results
from curvesim.pipelines import run_pipeline
from curvesim.pipelines.simple.strategy import SimpleStrategy

from ..common import DEFAULT_METRICS, get_asset_data, get_pool_data


def pipeline(  # pylint: disable=too-many-locals
    metadata_or_address,
    *,
    chain="mainnet",
    variable_params=None,
    fixed_params=None,
    src="coingecko",
    time_sequence=None,
    pool_ts=None,
    ncpu=None,
    env="prod",
):
    """
    Implements the simple arbitrage pipeline.  This is a very simplified version
    of :func:`curvesim.pipelines.vol_limited_arb.pipeline`.

    At each timestep, the pool is arbitraged as close to the prevailing market
    price as possible for the coin pair generating the largest arbitrage profit.

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

    src : str or :class:`~curvesim.templates.DateSource`, default="coingecko"
        Source for price/volume data: "coingecko" or "local".

    time_sequence : :class:`~curvesim.templates.DateTimeSequence`, optional
        Timepoints for price/volume data and simulated trades.

    pool_ts : datetime.datetime or int, optional
        Optional timestamp to use when fetching metadata by address.

    ncpu : int, default=os.cpu_count()
        Number of cores to use.

    Returns
    -------
    :class:`~curvesim.metrics.SimResults`

    """
    ncpu = ncpu or os.cpu_count()

    pool, pool_metadata = get_pool_data(metadata_or_address, chain, env, pool_ts)
    asset_data, _ = get_asset_data(pool_metadata, time_sequence, src)

    # pylint: disable-next=abstract-class-instantiated
    param_sampler = ParameterizedPoolIterator(pool, variable_params, fixed_params)
    price_sampler = PriceVolume(asset_data)

    _metrics = init_metrics(DEFAULT_METRICS, pool=pool)
    strategy = SimpleStrategy(_metrics)

    output = run_pipeline(param_sampler, price_sampler, strategy, ncpu=ncpu)
    results = make_results(*output, _metrics)
    return results
