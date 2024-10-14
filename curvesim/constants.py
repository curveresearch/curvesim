"""
Constants and Enum types used in Curvesim.
"""
from enum import Enum


class StrEnum(str, Enum):
    """
    Custom string enum type since the builtin `StrEnum` is not available
    until Python 3.11.
    """

    def __str__(self):
        """
        Regular Enum's __str__ is the name, rather than the value,
        e.g.

        >>> str(Chain.MAINNET)
        'Chain.MAINNET'

        so we need to explicitly use the value.

        This behaves like the builtin `StrEnum` (available in 3.11).
        """
        return str.__str__(self)


class Chain(StrEnum):
    """Identifiers for chains & layer 2s."""

    MAINNET = "mainnet"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"
    FANTOM = "fantom"
    AVALANCHE = "avalanche"
    MATIC = "matic"
    XDAI = "xdai"
    BASE = "base"
    FRAXTAL = "fraxtal"


class Env(StrEnum):
    """Names for different API environments."""

    PROD = "prod"
    STAGING = "staging"


class CurvePreset(StrEnum):
    """Names for presets within Curve.fi's pool creation UI."""
    # Stableswap
    FIAT_REDEEMDABLE_STABLECOINS = "fiat redeemable stablecoins"
    CRYPTO_COLLATERALIZED_STABLECOINS = "crypto collateralized stablecoins"
    STABLESWAP_LIQUID_RESTAKING_TOKENS = "stableswap liquid restaking tokens"
    # Cryptoswap
    CRYPTO = "crypto"
    FOREX = "forex"
    LIQUID_STAKING_DERIVATIVES = "liquid staking derivatives"
    CRYPTOSWAP_LIQUID_RESTAKING_TOKENS = "cryptoswap liquid restaking tokens"
    # Tricrypto
    TRICRYPTO = "tricrypto" # USD-wrapped BTC-ETH
    THREE_COIN_VOLATILE = "three coin volatile" # USD-ETH-any volatile token
