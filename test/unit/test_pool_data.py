import json

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
        ]
    },
    "reserves": {
        "D": 514826120522625451905251599,
        "by_coin": [
            179381510785466069567452867,
            187328030484252000000000000,
            148116579252947000000000000
        ],
        "virtual_price": 1023909069246875343,
        "tokens": 502804532145906220672195720
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
            ]
        },
        "reserves": {
            "D": 10161589995019295303676745,
            "by_coin": [4728546370000000000000000, 5433043628290853888692995],
            "virtual_price": 1001157649971074853,
            "tokens": 10149840032998679996759468
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
                "fee_mul": null
            },
            "coins": {
                "names": ["FRAX", "USDC"],
                "addresses": [
                    "0x853d955aCEf822Db058eb8505911ED77F175b99e",
                    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
                ]
            },
            "reserves": {
                "D": 531637583549759155083838474,
                "by_coin": [
                    343337761102313831582756229,
                    188299825741459000000000000
                ],
                "virtual_price": 1001135892736485329,
                "tokens": 531034385448504248618512230
            },
            "basepool": null,
            "timestamp": 1677715200
        },
        "timestamp": 1677715200
}
"""

# TODO; this needs to be updated once we have v2 snapshots
CRYPTOPOOL_TEST_METADATA_JSON = """
{
    "name": "Curve.fi Factory Crypto Pool: STG/USDC",
    "address": "0x3211C6cBeF1429da3D0d58494938299C92Ad5860",
    "chain": "mainnet",
    "symbol": "STGUSDC-f",
    "version": 2,
    "pool_type": "CRYPTO_FACTORY",
    "params": {"A": 400000, "fee": 40971769, "fee_mul": null},
    "coins": {
        "names": ["STG", "USDC"],
        "addresses": [
            "0xAf5191B0De278C7286d6C7CC6ab6BB8A73bA2Cd6",
            "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"]
    },
    "reserves": {
        "D": 27009344624167129044473141,
        "by_coin": [
            13497126535708129065554254,
            13512218088459000000000000
        ],
        "virtual_price": 1031212780979726100,
        "tokens": 26191824929192900959501494
    },
    "basepool": null,
    "timestamp": 1677715200
}
"""

pool_test_metadata = json.loads(POOL_TEST_METADATA_JSON)
metapool_test_metadata = json.loads(METAPOOL_TEST_METADATA_JSON)
cryptopool_test_metadata = json.loads(CRYPTOPOOL_TEST_METADATA_JSON)


def test_pool_data():
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

    assert metadata.has_redemption_prices is False

    assert metadata.init_kwargs() == {
        "A": 2000,
        "D": 514826120522625451905251599,
        "n": 3,
        "fee": 1000000,
        "fee_mul": None,
        "tokens": 502804532145906220672195720,
    }
    assert metadata.init_kwargs(balanced=False) == {
        "A": 2000,
        "D": [
            179381510785466069567452867,
            187328030484252000000000000,
            148116579252947000000000000,
        ],
        "n": 3,
        "fee": 1000000,
        "fee_mul": None,
        "tokens": 502804532145906220672195720,
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

    assert metadata.has_redemption_prices is False

    init_kwargs = metadata.init_kwargs()
    _ = init_kwargs.pop("basepool")

    assert init_kwargs == {
        "A": 1500,
        "D": 10161589995019295303676745,
        "n": 2,
        "fee": 4000000,
        "fee_mul": None,
        "tokens": 10149840032998679996759468,
    }

    unbalanced_init_kwargs = metadata.init_kwargs(balanced=False)
    _ = unbalanced_init_kwargs.pop("basepool")

    assert unbalanced_init_kwargs == {
        "A": 1500,
        "D": [4728546370000000000000000, 5433043628290853888692995],
        "n": 2,
        "fee": 4000000,
        "fee_mul": None,
        "tokens": 10149840032998679996759468,
    }
