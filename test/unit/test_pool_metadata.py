import json

from curvesim.pool.cryptoswap.pool import CurveCryptoPool
from curvesim.pool.sim_interface.metapool import SimCurveMetaPool
from curvesim.pool.sim_interface.pool import SimCurvePool
from curvesim.pool.stableswap.metapool import CurveMetaPool
from curvesim.pool.stableswap.pool import CurvePool
from curvesim.pool_data.metadata import PoolMetaData

POOL_TEST_METADATA_JSON = """
{
    "name": "Curve.fi DAI/USDC/USDT",
    "address": "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",
    "chain": "mainnet",
    "symbol": "3Crv",
    "version": 1,
    "pool_type": "REGISTRY_V1",
    "params": {"A": 2000, "fee": 1000000, "fee_mul": null},
    "coins": {
        "names": ["DAI", "USDC", "USDT"],
        "addresses": [
            "0x6B175474E89094C44Da98b954EedeAC495271d0F",
            "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "0xdAC17F958D2ee523a2206206994597C13D831ec7"
        ],
        "decimals": [18, 6, 6]
    },
    "reserves": {
        "D": 435874505461314832883219554,
        "by_coin": [
            171485829393046867353492287,
            175414686134396000000000000,
            88973989934190000000000000
        ],
        "unnormalized_by_coin": [
            171485829393046867353492287,
            175414686134396,
            88973989934190
        ],
        "virtual_price": 1025499623208090719,
        "tokens": 425036241454443455995211818
    },
    "basepool": null,
    "timestamp": 1677628800
}
"""

METAPOOL_TEST_METADATA_JSON = """
{
    "name": "Curve.fi Factory USD Metapool: GUSDFRAXBP",
    "address": "0x4e43151b78b5fbb16298C1161fcbF7531d5F8D93",
    "chain":"mainnet",
    "symbol": "GUSDFRAXBP3CRV-f",
    "version": 1,
    "pool_type": "STABLE_FACTORY",
    "params": {
        "A": 1500, "fee": 4000000, "fee_mul": null},
        "coins": {
            "names": ["GUSD", "crvFRAX"],
            "addresses": [
                "0x056Fd409E1d7A124BD7017459dFEa2F387b6d5Cd",
                "0x3175Df0976dFA876431C2E9eE6Bc45b65d3473CC"
            ],
            "decimals": [2, 18]
        },
        "reserves": {
            "D": 9165154506890406219227550,
            "by_coin": [4580491420000000000000000, 4584663086890532793313572],
            "unnormalized_by_coin": [458049142, 4584663086890532793313572],
            "virtual_price": 1002128768748324821,
            "tokens": 9145685457506457679415433
        },
        "basepool": {
            "name": "Curve.fi FRAX/USDC",
            "address": "0xDcEF968d416a41Cdac0ED8702fAC8128A64241A2",
            "chain": "mainnet",
            "symbol": "crvFRAX",
            "version": 1,
            "pool_type":
            "REGISTRY_V1",
            "params": {
                "A": 1500,
                "fee": 1000000,
                "fee_mul": null,
                "admin_fee": 5000000000
            },
            "coins": {
                "names": ["FRAX", "USDC"],
                "addresses": [
                    "0x853d955aCEf822Db058eb8505911ED77F175b99e",
                    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
                ],
                "decimals": [18, 6]
            },
            "reserves": {
                "D": 492801294421778420804073827,
                "by_coin": [305660498155854651779818562, 187140798282666000000000000],
                "unnormalized_by_coin": [305660498155854651779818562, 187140798282666],
                "virtual_price": 1001200369105166674,
                "tokens": 492210460192123924194896848
            },
            "basepool": null,
            "timestamp": 1677715200
        },
        "timestamp": 1677715200
}
"""

CRYPTOPOOL_TEST_METADATA_JSON = """
{
    "name": "Curve.fi Factory Crypto Pool: STG/USDC",
    "address": "0x3211C6cBeF1429da3D0d58494938299C92Ad5860",
    "chain": "mainnet",
    "symbol": "STGUSDC-f",
    "version": 2,
    "pool_type": "CRYPTO_FACTORY",
    "params": {
        "A": 400000,
        "gamma": 72500000000000,
        "fee_gamma": 230000000000000,
        "mid_fee": 26000000,
        "out_fee": 45000000,
        "allowed_extra_profit": 2000000000000,
        "adjustment_step": 146000000000000,
        "ma_half_time": 146000000000000,
        "price_scale": 1532848669525694314,
        "price_oracle": 1629891359676425537,
        "last_prices": 1625755383082188296,
        "last_prices_timestamp": 1684107935,
        "admin_fee": 5000000000,
        "xcp_profit": 1073065310463073367,
        "xcp_profit_a": 1073065310463073367
    },
    "coins": {
        "names": ["STG", "USDC"],
        "addresses": [
            "0xAf5191B0De278C7286d6C7CC6ab6BB8A73bA2Cd6",
            "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
        ],
        "decimals": [18, 6]
    },
    "reserves": {
        "D": 18116170684879887969148488,
        "by_coin": [11278350350009782994292193, 6837820334873000000000000],
        "unnormalized_by_coin": [11278350350009782994292193, 6837820334873],
        "virtual_price": 1036543672382221695,
        "tokens": 17477479403491661243983086
    },
    "basepool": null,
    "timestamp": 1684108800
}
"""

pool_test_metadata = json.loads(POOL_TEST_METADATA_JSON)
metapool_test_metadata = json.loads(METAPOOL_TEST_METADATA_JSON)
cryptopool_test_metadata = json.loads(CRYPTOPOOL_TEST_METADATA_JSON)


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
        "D": 435874505461314832883219554,
        "n": 3,
        "fee": 1000000,
        "fee_mul": None,
        "tokens": 425036241454443455995211818,
    }
    assert metadata.init_kwargs(balanced=False) == {
        "A": 2000,
        "D": [
            171485829393046867353492287,
            175414686134396000000000000,
            88973989934190000000000000,
        ],
        "n": 3,
        "fee": 1000000,
        "fee_mul": None,
        "tokens": 425036241454443455995211818,
    }
    assert metadata.init_kwargs(balanced=False, normalize=False) == {
        "A": 2000,
        "D": [
            171485829393046867353492287,
            175414686134396,
            88973989934190,
        ],
        "n": 3,
        "fee": 1000000,
        "fee_mul": None,
        "tokens": 425036241454443455995211818,
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
    _ = init_kwargs.pop("basepool")

    assert init_kwargs == {
        "A": 1500,
        "D": 9165154506890406219227550,
        "n": 2,
        "fee": 4000000,
        "fee_mul": None,
        "tokens": 9145685457506457679415433,
    }

    unbalanced_init_kwargs = metadata.init_kwargs(balanced=False)
    del unbalanced_init_kwargs["basepool"]

    assert unbalanced_init_kwargs == {
        "A": 1500,
        "D": [4580491420000000000000000, 4584663086890532793313572],
        "n": 2,
        "fee": 4000000,
        "fee_mul": None,
        "tokens": 9145685457506457679415433,
    }

    unnormalized_init_kwargs = metadata.init_kwargs(balanced=False, normalize=False)
    del unnormalized_init_kwargs["basepool"]

    assert unnormalized_init_kwargs == {
        "A": 1500,
        "D": [458049142, 4584663086890532793313572],
        "n": 2,
        "fee": 4000000,
        "fee_mul": None,
        "tokens": 9145685457506457679415433,
        "rate_multiplier": 10000000000000000000000000000000000,
    }


def test_cryptopool():
    metadata = PoolMetaData(cryptopool_test_metadata)

    assert metadata.address == "0x3211C6cBeF1429da3D0d58494938299C92Ad5860"
    assert metadata.chain == "mainnet"

    assert metadata.pool_type == CurveCryptoPool
    # TODO: create sim pool for crypto pools
    # assert metadata.sim_pool_type == SimCurveCryptoPool

    assert metadata.coin_names == ["STG", "USDC"]
    assert metadata.coins == [
        "0xAf5191B0De278C7286d6C7CC6ab6BB8A73bA2Cd6",
        "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    ]

    assert metadata.n == 2

    assert metadata.init_kwargs() == {
        "A": 400000,
        "gamma": 72500000000000,
        "D": 18116170684879887969148488,
        "n": 2,
        "mid_fee": 26000000,
        "out_fee": 45000000,
        "adjustment_step": 146000000000000,
        "allowed_extra_profit": 2000000000000,
        "fee_gamma": 230000000000000,
        "tokens": 17477479403491661243983086,
        "ma_half_time": 146000000000000,
        "price_scale": 1532848669525694314,
        "xcp_profit": 1073065310463073367,
        "xcp_profit_a": 1073065310463073367,
    }
    assert metadata.init_kwargs(balanced=False) == {
        "A": 400000,
        "gamma": 72500000000000,
        "D": 18116170684879887969148488,
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
        "tokens": 17477479403491661243983086,
        "ma_half_time": 146000000000000,
        "price_scale": 1532848669525694314,
        "xcp_profit": 1073065310463073367,
        "xcp_profit_a": 1073065310463073367,
    }
    assert metadata.init_kwargs(balanced=False, normalize=False) == {
        "A": 400000,
        "gamma": 72500000000000,
        "D": 18116170684879887969148488,
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
        "tokens": 17477479403491661243983086,
        "ma_half_time": 146000000000000,
        "price_scale": 1532848669525694314,
        "xcp_profit": 1073065310463073367,
        "xcp_profit_a": 1073065310463073367,
        "precisions": [
            1,
            1000000000000,
        ],
    }
