from enum import Enum


class Chain(str, Enum):
    MAINNET = "mainnet"
    ARBITRUM = "arbitrum"
    OPTIMISM = "optimism"
    FANTOM = "fantom"
    AVALANCHE = "avalanche"
    MATIC = "matic"
    XDAI = "xdai"


class Env(str, Enum):
    PROD = "prod"
    STAGING = "staging"
