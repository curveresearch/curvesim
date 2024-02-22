from curvesim.pool.sim_interface import SimCurveMetaPool, SimCurvePool
from curvesim.pool.stableswap import CurveMetaPool, CurvePool
from curvesim.pool_data import get_metadata

properties = ["chain", "pool_type", "sim_pool_type", "coins", "coin_names", "n"]

# To generate stored properties for a pool:
# stored_properties = {}
# for p in properties:
#      stored_properties[p] = getattr(metadata, p)


def _test_pool_metadata(address, chain, stored_properties, stored_dict):
    metadata = get_metadata(address, chain)
    metadata_dict = metadata._dict

    # Remove non-static items from dict
    del metadata_dict["timestamp"], metadata_dict["reserves"], metadata_dict["params"]

    if metadata_dict["basepool"] is not None:
        del (
            metadata_dict["basepool"]["timestamp"],
            metadata_dict["basepool"]["reserves"],
            metadata_dict["basepool"]["params"],
        )

    for p in properties:
        assert stored_properties[p] == getattr(
            metadata, p
        ), f"Metadata property '{p}' did not match for {chain}:{address}"

    assert (
        metadata_dict == stored_dict
    ), f"Metadata dict did not match for {chain}:{address}"


def test_lending_pool_metadata():
    # a3crv
    address = "0xDeBF20617708857ebe4F679508E7b7863a8A8EeE"
    chain = "mainnet"

    stored_properties = {
        "chain": "mainnet",
        "pool_type": CurvePool,
        "sim_pool_type": SimCurvePool,
        "coins": [
            "0x6B175474E89094C44Da98b954EedeAC495271d0F",
            "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        ],
        "coin_names": ["DAI", "USDC", "USDT"],
        "n": 3,
    }

    stored_dict = {
        "name": "Curve.fi aDAI/aUSDC/aUSDT",
        "address": "0xDeBF20617708857ebe4F679508E7b7863a8A8EeE",
        "chain": "mainnet",
        "symbol": "a3CRV",
        "version": 1,
        "pool_type": "LENDING",
        "basepool": None,
        "coins": {
            "names": ["DAI", "USDC", "USDT"],
            "addresses": [
                "0x6B175474E89094C44Da98b954EedeAC495271d0F",
                "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            ],
            "decimals": [18, 6, 6],
            "wrapper": {
                "names": ["aDAI", "aUSDC", "aUSDT"],
                "addresses": [
                    "0x028171bCA77440897B824Ca71D1c56caC55b68A3",
                    "0xBcca60bB61934080951369a648Fb03DF4F96263C",
                    "0x3Ed3B47Dd13EC9a98b44e6204A523E766B225811",
                ],
                "decimals": [18, 6, 6],
            },
        },
    }

    _test_pool_metadata(address, chain, stored_properties, stored_dict)


def test_l2_pool_metadata():
    # 2crv
    address = "0x7f90122BF0700F9E7e1F688fe926940E8839F353"
    chain = "arbitrum"

    stored_properties = {
        "chain": "arbitrum",
        "pool_type": CurvePool,
        "sim_pool_type": SimCurvePool,
        "coins": [
            "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",
            "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
        ],
        "coin_names": ["USDC", "USDT"],
        "n": 2,
    }

    stored_dict = {
        "name": "Curve.fi USDC/USDT",
        "address": "0x7f90122BF0700F9E7e1F688fe926940E8839F353",
        "chain": "arbitrum",
        "symbol": "2CRV",
        "version": 1,
        "pool_type": "REGISTRY_V1",
        "basepool": None,
        "coins": {
            "names": ["USDC", "USDT"],
            "addresses": [
                "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",
                "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
            ],
            "decimals": [6, 6],
        },
    }

    _test_pool_metadata(address, chain, stored_properties, stored_dict)


def test_mainnet_metapool_metadata():
    # OUSD
    address = "0x87650d7bbfc3a9f10587d7778206671719d9910d"
    chain = "mainnet"

    stored_properties = {
        "chain": "mainnet",
        "pool_type": CurveMetaPool,
        "sim_pool_type": SimCurveMetaPool,
        "coins": [
            "0x2A8e1E676Ec238d8A992307B495b45B3fEAa5e86",
            "0x6B175474E89094C44Da98b954EedeAC495271d0F",
            "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        ],
        "coin_names": ["OUSD", "DAI", "USDC", "USDT"],
        "n": [2, 3],
    }

    stored_dict = {
        "name": "Curve.fi Factory USD Metapool: Origin Dollar",
        "address": "0x87650D7bbfC3A9F10587d7778206671719d9910D",
        "chain": "mainnet",
        "symbol": "OUSD3CRV-f",
        "version": 1,
        "pool_type": "METAPOOL_FACTORY",
        "basepool": {
            "name": "Curve.fi DAI/USDC/USDT",
            "address": "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",
            "chain": "mainnet",
            "symbol": "3Crv",
            "version": 1,
            "pool_type": "REGISTRY_V1",
            "coins": {
                "names": ["DAI", "USDC", "USDT"],
                "addresses": [
                    "0x6B175474E89094C44Da98b954EedeAC495271d0F",
                    "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
                    "0xdAC17F958D2ee523a2206206994597C13D831ec7",
                ],
                "decimals": [18, 6, 6],
            },
            "basepool": None,
        },
        "coins": {
            "names": ["OUSD", "3Crv"],
            "addresses": [
                "0x2A8e1E676Ec238d8A992307B495b45B3fEAa5e86",
                "0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490",
            ],
            "decimals": [18, 18],
        },
    }

    _test_pool_metadata(address, chain, stored_properties, stored_dict)
