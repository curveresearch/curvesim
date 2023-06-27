import os

from curvesim.iterators.param_samplers import Grid
from curvesim.iterators.price_samplers import PriceVolume
from curvesim.metrics import init_metrics
from curvesim.metrics import metrics as Metrics
from curvesim.metrics.results import make_results
from curvesim.pipelines import run_pipeline
from curvesim.pipelines.simple.strategy import SimpleStrategy
from curvesim.pool import get_sim_pool

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


def pipeline(
    pool_address,
    chain,
    variable_params=None,
    fixed_params=None,
    test=False,
    end_ts=None,
    days=60,
    src="coingecko",
    data_dir="data",
    ncpu=None,
):
    """
    Implements the simple arbitrage pipeline.  This is a very simplified version of the
    :func:`volume-limited arbitrage pipeline<curvesim.pipelines.vol_limited_arb.pipeline>`.

    At each timestep, the pool is arbitraged as close to the prevailing market price
    as possible for the coin pair generating the largest arbitrage profit.

    Parameters
    ----------
    pool_address : str
        '0x'-prefixed string representing the pool address.

    chain: str
        Identifier for blockchain or layer2.  Supported values are:
        "mainnet", "arbitrum", "optimism", "fantom", "avalanche", "matic", "xdai"

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

    end_ts : int, optional
        End timestamp in Unix time.  Defaults to 30 minutes before midnight of the
        current day in UTC.

    days : int, default=60
        Number of days to pull price/volume data for.

    src : str, default="coingecko"
        Source for price/volume data: "coingecko" or "local".

    data_dir : str, default="data"
        relative path to saved price data folder

    ncpu : int, default=os.cpu_count()
        Number of cores to use.

    Returns
    -------
    :class:`~curvesim.metrics.SimResults`

    """
    ncpu = ncpu or os.cpu_count()

    pool = get_sim_pool(pool_address, chain, end_ts=end_ts)

    sim_assets = pool.assets
    price_sampler = PriceVolume(
        sim_assets, days=days, end=end_ts, data_dir=data_dir, src=src
    )

    variable_params = variable_params or DEFAULT_PARAMS
    fixed_params = fixed_params or {}

    if test:
        variable_params = TEST_PARAMS
        fixed_params = {}

    param_sampler = Grid(pool, variable_params, fixed_params=fixed_params)

    _metrics = init_metrics(DEFAULT_METRICS, pool=pool)
    strategy = SimpleStrategy(_metrics)

    output = run_pipeline(param_sampler, price_sampler, strategy, ncpu=ncpu)
    results = make_results(*output, _metrics)
    return results
