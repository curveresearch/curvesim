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


class Env(StrEnum):
    """Names for different API environments."""

    PROD = "prod"
    STAGING = "staging"
