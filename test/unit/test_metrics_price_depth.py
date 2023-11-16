from numpy import inf, mean

from curvesim.metrics.metrics import _compute_liquidity_density
from curvesim.utils import get_pairs


def test_liquidity_density_sim_curve_pool(sim_curve_pool):
    _test_liquidity_density_stableswap(sim_curve_pool)


def test_liquidity_density_sim_curve_tripool(sim_curve_tripool):
    _test_liquidity_density_stableswap(sim_curve_tripool)


def test_liquidity_density_sim_curve_meta_pool(sim_curve_meta_pool):
    basepool = sim_curve_meta_pool.basepool
    coin_names = ["BP_SYM" + str(i) for i in range(basepool.n)]
    basepool.metadata = {"coins": {"names": coin_names}}
    _test_liquidity_density_stableswap(sim_curve_meta_pool)


def test_liquidity_density_sim_curve_crypto_pool(sim_curve_crypto_pool):
    _test_liquidity_density_cryptoswap(sim_curve_crypto_pool)


def test_liquidity_density_sim_curve_tricrypto_pool(sim_curve_tricrypto_pool):
    _test_liquidity_density_cryptoswap(sim_curve_tricrypto_pool)


def _test_liquidity_density_stableswap(pool):
    """
    Tests liquidity density for stableswap pools:
    - Ensure LD is max at center
    - Ensure LDs ~equal at equivalent curve positions for every trading pair/direction
    - Ensure LD at center is ~correct
    """

    def trade_size_function(pool, coin_in):
        x_per_dx = 10**8
        return pool.asset_balances[coin_in] // x_per_dx

    A_list = [10, 50, 100, 500, 1000, 5000]
    for A in A_list:
        pool.A = A
        LD_range = _test_compute_liquidity_density(pool, trade_size_function)

        # Ensure LD at center is ~correct
        LD_max_expected = (A + 1) / 2
        assert abs(LD_range[0] - LD_max_expected) / LD_max_expected < 0.001


def _test_liquidity_density_cryptoswap(pool):
    """
    Tests liquidity density for cryptoswap pools:
    - Ensure LD is max at center
    - Ensure LDs ~equal at equivalent curve positions for every trading pair/direction
    - Ensure LD at center is ~correct
    - Ensure LD near tail is ~.5 (constant product LD)
    """

    def trade_size_function(pool, coin_in):
        return pool.get_min_trade_size(coin_in)

    pool.allowed_extra_profit = inf  # disable _tweak_price
    pool.balances = pool._convert_D_to_balances(pool.D)  # balance pool
    n = pool.n

    A_list = [10, 50, 100, 500]
    gamma_list = [10**x for x in range(13, 16)]
    for A in A_list:
        for gamma in gamma_list:
            pool.A = A * n**n * 10000
            pool.gamma = gamma
            LD_range = _test_compute_liquidity_density(pool, trade_size_function)

            # Ensure LD at center is ~correct
            A_v1 = A * n ** (n - 1)
            LD_max_expected = (A_v1 + 1) / 2
            assert abs(LD_range[0] - LD_max_expected) / LD_max_expected < 0.0015

            # Ensure LD near tail is ~.5 (constant product LD)
            assert 0.47 < LD_range[-1] < 0.501


def _test_compute_liquidity_density(pool, trade_size_fn):
    """
    Computes liquidity density ranges for each trading pair/direction and tests that:
    - LD is max at center
    - LDs ~equal at equivalent curve positions
    """
    coin_names = ["SYM" + str(i) for i in range(pool.n)]
    pool.metadata = {"coins": {"names": coin_names}}

    # Compute LD range for each trading pair/direction
    coin_pairs = get_pairs(pool.coin_names)
    LD_ranges = []
    for pair in coin_pairs:
        coin_in, coin_out = pair
        LD0 = _compute_liquidity_density_range(pool, coin_in, coin_out, trade_size_fn)
        LD1 = _compute_liquidity_density_range(pool, coin_out, coin_in, trade_size_fn)
        LD_ranges += [LD0, LD1]

    # Ensure LD is max at center
    for LD_range in LD_ranges:
        assert LD_range[0] == max(LD_range)

    # Ensure LDs ~equal at equivalent curve positions for every trading pair/direction
    LD_ranges_aligned = list(zip(*LD_ranges))
    LD_ranges_means = [mean(LDs) for LDs in LD_ranges_aligned]
    for LDs, LD_mean in zip(LD_ranges_aligned, LD_ranges_means):
        percent_deviations = [abs(LD - LD_mean) / LD_mean for LD in LDs]
        assert max(percent_deviations) < 1e-4

    return LD_ranges_means


def _compute_liquidity_density_range(pool, coin_in, coin_out, trade_size_function):
    """Computes liquidity density at a range of locations along the bonding curve."""

    pre_trade_size = 0
    pre_trade_step_size = pool.asset_balances[coin_in] // 250

    coin_out_balances = pool.asset_balances[coin_out]
    coin_out_balances_limit = coin_out_balances * 0.05

    LD_range = []
    while coin_out_balances > coin_out_balances_limit:
        with pool.use_snapshot_context():
            if pre_trade_size > 0:
                pool.trade(coin_in, coin_out, pre_trade_size)
            LD_trade_size = trade_size_function(pool, coin_in)
            LD = _compute_liquidity_density(pool, coin_in, coin_out, LD_trade_size)
            coin_out_balances = pool.asset_balances[coin_out]

        LD_range.append(LD)
        pre_trade_size += pre_trade_step_size

    return LD_range
