from curvesim.metrics import init_metrics, metrics

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


def pipeline(ncpu=1):
    pool_metadata = pool_metadata or get_metadata(pool, chain)
    pool = get_sim_pool(pool_metadata, pool_data_cache=pool_data_cache)
    param_sampler = Grid(pool, variable_params, fixed_params=fixed_params)
    price_sampler = PriceVolume(coins, days=days, data_dir=data_dir, src=src, end=end)

    metrics = init_metrics(metrics, pool=pool, freq=price_sampler.freq)
    strategy = SimpleStrategy(metrics, vol_mult)

    output = run_pipeline(param_sampler, price_sampler, strategy, ncpu=ncpu)
    results = make_results(*output, metrics)
