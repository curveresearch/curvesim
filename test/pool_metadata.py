import json

POOL_TEST_METADATA_JSON = """
{
    "name": "Curve.fi DAI/USDC/USDT",
    "address": "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",
    "chain": "mainnet",
    "symbol": "3Crv",
    "version": 1,
    "pool_type": "REGISTRY_V1",
    "params": {"A": 2000, "fee": 1000000, "fee_mul": null, "admin_fee": 5000000000},
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
        "virtual_price": 1025499623208090719
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
        "A": 1500, "fee": 4000000, "fee_mul": null, "admin_fee": 5000000000},
        "coins": {
            "names": ["GUSD", "crvFRAX"],
            "addresses": [
                "0x056Fd409E1d7A124BD7017459dFEa2F387b6d5Cd",
                "0x3175Df0976dFA876431C2E9eE6Bc45b65d3473CC"
            ],
            "decimals": [2, 18]
        },
        "reserves": {
            "by_coin": [4580491420000000000000000, 4584663086890532793313572],
            "unnormalized_by_coin": [458049142, 4584663086890532793313572],
            "virtual_price": 1002128768748324821
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
                "by_coin": [305660498155854651779818562, 187140798282666000000000000],
                "unnormalized_by_coin": [305660498155854651779818562, 187140798282666],
                "virtual_price": 1001200369105166674
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
        "ma_half_time": 600,
        "price_scale": [1532848669525694314],
        "price_oracle": [1629891359676425537],
        "last_prices": [1625755383082188296],
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
        "by_coin": [11278350350009782994292193, 6837820334873000000000000],
        "unnormalized_by_coin": [11278350350009782994292193, 6837820334873],
        "virtual_price": 1036543672382221695
    },
    "basepool": null,
    "timestamp": 1684108800
}
"""

TRICRYPTO_NG_TEST_METADATA_JSON = """
{
    "name": "TriCRV",
    "address": "0x4eBdF703948ddCEA3B11f675B4D1Fba9d2414A14",
    "chain": "mainnet",
    "symbol": "crvUSDETHCRV",
    "version": 2,
    "pool_type": "TRICRYPTO_FACTORY",
    "params": {
        "A": 2700000,
        "gamma": 1300000000000,
        "fee_gamma": 350000000000000,
        "mid_fee": 2999999,
        "out_fee": 80000000,
        "allowed_extra_profit": 100000000000,
        "adjustment_step": 100000000000,
        "ma_half_time": 600,
        "price_scale": [1649177296373068449425, 446562202678699631],
        "price_oracle": [1648041807040538375682, 447066843075586148],
        "last_prices": [1645044680220385710284, 446876572801432826],
        "last_prices_timestamp": 1694130839,
        "admin_fee": 5000000000,
        "xcp_profit": 1018853337326661730,
        "xcp_profit_a": 1018852684256364084
    },
    "coins": {
        "names": ["crvUSD", "WETH", "CRV"],
        "addresses": [
            "0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E",
            "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            "0xD533a949740bb3306d119CC777fa900bA034cd52"
        ],
        "decimals": [18, 18, 18]
    },
    "reserves": {
        "by_coin": [
            3724679717441585468224357,
            2268620966125133833261,
            8327951931226366295069133
        ],
        "unnormalized_by_coin": [
            3724679717441585468224357,
            2268620966125133833261,
            8327951931226366295069133
        ],
        "virtual_price": 1027263450430060608
    },
    "basepool": null,
    "timestamp": 1694131200
}
"""

pool_test_metadata = json.loads(POOL_TEST_METADATA_JSON)
metapool_test_metadata = json.loads(METAPOOL_TEST_METADATA_JSON)
cryptopool_test_metadata = json.loads(CRYPTOPOOL_TEST_METADATA_JSON)
tricrypto_ng_test_metadata = json.loads(TRICRYPTO_NG_TEST_METADATA_JSON)
