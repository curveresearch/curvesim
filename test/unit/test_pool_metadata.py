from curvesim.pool.cryptoswap.pool import CurveCryptoPool
from curvesim.pool.sim_interface.cryptoswap import SimCurveCryptoPool
from curvesim.pool.sim_interface.metapool import SimCurveMetaPool
from curvesim.pool.sim_interface.pool import SimCurvePool
from curvesim.pool.stableswap.metapool import CurveMetaPool
from curvesim.pool.stableswap.pool import CurvePool
from curvesim.pool_data.metadata import PoolMetaData

from ..pool_metadata import (
    cryptopool_test_metadata,
    metapool_test_metadata,
    pool_test_metadata,
    tricrypto_ng_test_metadata,
)


def test_pool():
    metadata = PoolMetaData(pool_test_metadata)

    assert metadata.address == "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"
    assert metadata.chain == "mainnet"

    assert metadata.pool_type == CurvePool
    assert metadata.sim_pool_type == SimCurvePool

    assert metadata.coin_names == ["DAI", "USDC", "USDT"]
    assert metadata.coins == [
        "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    ]

    assert metadata.n == 3

    assert metadata.pool_type is CurvePool

    assert metadata.init_kwargs() == {
        "A": 2000,
        "D": [
            171485829393046867353492287,
            175414686134396000000000000,
            88973989934190000000000000,
        ],
        "n": 3,
        "fee": 1000000,
        "fee_mul": None,
        "admin_fee": 5000000000,
        "virtual_price": 1025499623208090719,
    }
    assert metadata.init_kwargs(normalize=False) == {
        "A": 2000,
        "D": [
            171485829393046867353492287,
            175414686134396,
            88973989934190,
        ],
        "n": 3,
        "fee": 1000000,
        "fee_mul": None,
        "admin_fee": 5000000000,
        "virtual_price": 1025499623208090719,
        "rates": [
            1000000000000000000,
            1000000000000000000000000000000,
            1000000000000000000000000000000,
        ],
    }


def test_metapool():
    metadata = PoolMetaData(metapool_test_metadata)

    assert metadata.address == "0x4e43151b78b5fbb16298C1161fcbF7531d5F8D93"
    assert metadata.chain == "mainnet"

    assert metadata.pool_type == CurveMetaPool
    assert metadata.sim_pool_type == SimCurveMetaPool

    assert metadata.coin_names == ["GUSD", "FRAX", "USDC"]
    assert metadata.coins == [
        "0x056Fd409E1d7A124BD7017459dFEa2F387b6d5Cd",
        "0x853d955aCEf822Db058eb8505911ED77F175b99e",
        "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    ]

    assert metadata.n == [2, 2]

    assert metadata.pool_type is CurveMetaPool

    init_kwargs = metadata.init_kwargs()
    del init_kwargs["basepool"]

    assert init_kwargs == {
        "A": 1500,
        "D": [4580491420000000000000000, 4584663086890532793313572],
        "n": 2,
        "fee": 4000000,
        "fee_mul": None,
        "admin_fee": 5000000000,
        "virtual_price": 1002128768748324821,
    }

    unnormalized_init_kwargs = metadata.init_kwargs(normalize=False)
    del unnormalized_init_kwargs["basepool"]

    assert unnormalized_init_kwargs == {
        "A": 1500,
        "D": [458049142, 4584663086890532793313572],
        "n": 2,
        "fee": 4000000,
        "fee_mul": None,
        "admin_fee": 5000000000,
        "virtual_price": 1002128768748324821,
        "rate_multiplier": 10000000000000000000000000000000000,
    }


def test_cryptopool():
    metadata = PoolMetaData(cryptopool_test_metadata)

    assert metadata.address == "0x3211C6cBeF1429da3D0d58494938299C92Ad5860"
    assert metadata.chain == "mainnet"

    assert metadata.pool_type == CurveCryptoPool
    assert metadata.sim_pool_type == SimCurveCryptoPool

    assert metadata.coin_names == ["STG", "USDC"]
    assert metadata.coins == [
        "0xAf5191B0De278C7286d6C7CC6ab6BB8A73bA2Cd6",
        "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    ]

    assert metadata.n == 2

    assert metadata.init_kwargs() == {
        "A": 400000,
        "gamma": 72500000000000,
        "balances": [
            11278350350009782994292193,
            6837820334873000000000000,
        ],
        "n": 2,
        "mid_fee": 26000000,
        "out_fee": 45000000,
        "adjustment_step": 146000000000000,
        "allowed_extra_profit": 2000000000000,
        "fee_gamma": 230000000000000,
        "virtual_price": 1036543672382221695,
        "ma_half_time": 600,
        "price_scale": [1532848669525694314],
        "admin_fee": 5000000000,
        "xcp_profit": 1073065310463073367,
        "xcp_profit_a": 1073065310463073367,
        "precisions": [1, 1],
    }
    assert metadata.init_kwargs(normalize=False) == {
        "A": 400000,
        "gamma": 72500000000000,
        "balances": [
            11278350350009782994292193,
            6837820334873,
        ],
        "n": 2,
        "mid_fee": 26000000,
        "out_fee": 45000000,
        "adjustment_step": 146000000000000,
        "allowed_extra_profit": 2000000000000,
        "fee_gamma": 230000000000000,
        "virtual_price": 1036543672382221695,
        "ma_half_time": 600,
        "price_scale": [1532848669525694314],
        "admin_fee": 5000000000,
        "xcp_profit": 1073065310463073367,
        "xcp_profit_a": 1073065310463073367,
        "precisions": [
            1,
            1000000000000,
        ],
    }


def test_tricrypto_ng():
    metadata = PoolMetaData(tricrypto_ng_test_metadata)

    assert metadata.address == "0x4eBdF703948ddCEA3B11f675B4D1Fba9d2414A14"
    assert metadata.chain == "mainnet"

    assert metadata.pool_type == CurveCryptoPool
    assert metadata.sim_pool_type == SimCurveCryptoPool

    assert metadata.coin_names == ["crvUSD", "WETH", "CRV"]
    assert metadata.coins == [
        "0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E",
        "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "0xD533a949740bb3306d119CC777fa900bA034cd52",
    ]

    assert metadata.n == 3

    assert metadata.init_kwargs() == {
        "A": 2700000,
        "gamma": 1300000000000,
        "balances": [
            3724679717441585468224357,
            2268620966125133833261,
            8327951931226366295069133,
        ],
        "n": 3,
        "mid_fee": 2999999,
        "out_fee": 80000000,
        "adjustment_step": 100000000000,
        "allowed_extra_profit": 100000000000,
        "fee_gamma": 350000000000000,
        "virtual_price": 1027263450430060608,
        "ma_half_time": 600,
        "price_scale": [1649177296373068449425, 446562202678699631],
        "admin_fee": 5000000000,
        "xcp_profit": 1018853337326661730,
        "xcp_profit_a": 1018852684256364084,
        "precisions": [1, 1, 1],
    }
    assert metadata.init_kwargs(normalize=False) == {
        "A": 2700000,
        "gamma": 1300000000000,
        "balances": [
            3724679717441585468224357,
            2268620966125133833261,
            8327951931226366295069133,
        ],
        "n": 3,
        "mid_fee": 2999999,
        "out_fee": 80000000,
        "adjustment_step": 100000000000,
        "allowed_extra_profit": 100000000000,
        "fee_gamma": 350000000000000,
        "virtual_price": 1027263450430060608,
        "ma_half_time": 600,
        "price_scale": [1649177296373068449425, 446562202678699631],
        "admin_fee": 5000000000,
        "xcp_profit": 1018853337326661730,
        "xcp_profit_a": 1018852684256364084,
        "precisions": [1, 1, 1],
    }
