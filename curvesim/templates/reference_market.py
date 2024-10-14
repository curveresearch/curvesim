from abc import ABC, abstractmethod
from typing import NewType, Dict, Any, List

from typing_extensions import Self

from curvesim.logging import get_logger
from curvesim.utils import override
from curvesim.iterators.price_samplers import PriceVolume, PriceVolumeSample

from .price_samplers import PriceSample
from .sim_asset import SimAsset, OnChainAssetPair

logger = get_logger(__name__)


# TimeStep = NewType("TimeStep", int)


class ReferenceMarket(ABC):
    """
    Fictionalized external venue used as a reference for trading strategies.
    """

    @abstractmethod
    def quotes(self, asset_pairs: List[OnChainAssetPair], timestamp: Any) -> PriceSample:
        """
        This particular signature supposes:
        - an infinite-depth external venue, i.e. we can trade at any size
          at the given price without market impact.
        - the "orderbook" is symmetric, i.e. trade direction doesn't matter.
        """
        raise NotImplementedError


class PriceVolumeReference(ReferenceMarket):
  """
  
  """
  def __init__(price_volume: PriceVolume):
    self.price_volume: PriceVolume = price_volume

  @override
  def quotes(self, asset_pairs: List[OnChainAssetPair], timestamp: Any) -> PriceVolumeSample:
    pass

  # PriceVolume doesn't have any restrictions on the timestamp index's type
  # so pass in any timestamp type, and if we can't find it, that's your fault

"""
- for now, could be a wrapper around pricevolume attr (or at least its .data df attr), basically simcontext.executor needs something to give price data for each timestamp in a timesequence
- prices signature should take in an AssetPair instead
  - needs to return a PriceSample (PriceVolumeSample)
- doesn't have data at a supplied timestamp - raise error
- abstract the timestamp? (ie local and coingecko may have different timesequence types)
  - assumptions rely on where you sourced the data from (should data sources have an interface for their timesequence type or read function sig. of whatever takes in timesequence? how do we know which data source was instantiated for the market in question?)
  - target type should be what? 

- pass referencemarket class in gin config like with log and trader
  - new referencemarket every run
  - simcontext needs to abstract the instantiation (data-passing) process for arbitrary referencemarket types
  - for the base class, what assumptions should we make (on the data and its structure)? what should we leave open?
    - data structure is dependent on outside operations, make assumption based on underlying data container

"""
