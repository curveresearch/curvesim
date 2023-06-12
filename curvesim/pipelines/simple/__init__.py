from curvesim.iterators.param_samplers import Grid
from curvesim.iterators.price_samplers import PriceVolume
from curvesim.metrics import init_metrics, metrics
from curvesim.metrics.results import make_results
from curvesim.pipelines import run_pipeline
from curvesim.pipelines.simple.strategy import SimpleStrategy
from curvesim.pool import get_sim_pool
from curvesim.pool_data import get_metadata

DEFAULT_METRICS = [
    metrics.Timestamp,
    metrics.PoolValue,
    metrics.PoolBalance,
    metrics.PriceDepth,
    metrics.ArbMetrics,
]

DEFAULT_PARAMS = {
    "A": [int(2 ** (a / 2)) for a in range(12, 28)],
    "fee": list(range(1000000, 5000000, 1000000)),
}

TEST_PARAMS = {"A": [100, 1000], "fee": [3000000, 4000000]}


def pipeline(pool_address, chain, ncpu=1):
    variable_params = DEFAULT_PARAMS
    fixed_params = {}
    days = 60
    pool_metadata = get_metadata(pool_address, chain)
    pool = get_sim_pool(pool_metadata)
    param_sampler = Grid(pool, variable_params, fixed_params=fixed_params)
    coin_addresses = pool.coin_addresses
    price_sampler = PriceVolume(coin_addresses, chain, days=days)

    metrics = DEFAULT_METRICS
    metrics = init_metrics(metrics, pool=pool)
    strategy = SimpleStrategy(metrics)

    output = run_pipeline(param_sampler, price_sampler, strategy, ncpu=ncpu)
    results = make_results(*output, metrics)
    return results


if __name__ == "__main__":
    pool_address = "0xbebc44782c7db0a1a60cb6fe97d0b483032ff1c7"
    chain = "mainnet"
    pipeline(pool_address, chain)
