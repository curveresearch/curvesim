"""Interfaces for SimAssets, which store data about assets used in simulations."""

from typing import NamedTuple

from curvesim.constants import Chain
from curvesim.utils import dataclass


@dataclass(frozen=True)
class SimAsset:
    """
    Base SimAsset dataclass to store data about assets used in simulations.

    Attributes
    ----------
    id : str
        Unique asset ID.

    symbol : str
        Asset symbol.
    """

    id: str
    symbol: str


@dataclass(frozen=True)
class OnChainAsset(SimAsset):
    """
    SimAsset dataclass to store data about on-chain assets.

    Attributes
    ----------
    id : str
        Unique asset ID.

    symbol : str
        Asset symbol.

    address : str
        Asset's blockchain address.

    chain : Chain
        Asset's blockchain.
    """

    address: str
    chain: Chain


class OnChainAssetPair(NamedTuple):
    """
    Container for base/quote pair of on-chain assets.

    Attributes
    ----------
    base : OnChainAsset
        The base asset.

    quote : OnChainAsset
        The quote asset.
    """

    base: OnChainAsset
    quote: OnChainAsset
