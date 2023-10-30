from enum import Enum


class StrEnum(str, Enum):
    def __str__(self):
        """
        Regular Enum's __str__ is the name, rather than the value,
        e.g.

        >>> str(Chain.MAINNET)
        'Chain.MAINNET'

        so we need to explicit use the value.

        This is not necessary in Python 3.11 or above, where the
        builtin `StrEnum` has this behavior.
        """
        return str.__str__(self)


class Chain(StrEnum):
    MAINNET = "mainnet"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"
    FANTOM = "fantom"
    AVALANCHE = "avalanche"
    MATIC = "matic"
    XDAI = "xdai"


class Env(StrEnum):
    PROD = "prod"
    STAGING = "staging"
