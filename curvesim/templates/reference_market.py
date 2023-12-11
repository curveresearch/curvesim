from abc import ABC, abstractmethod
from typing import List, NewType

from typing_extensions import Self

from curvesim.logging import get_logger

logger = get_logger(__name__)


TimeStep = NewType("TimeStep", int)


class SimAsset:
    id: str

    def __init__(self, _id: str) -> Self:
        self.id = _id


class ReferenceMarket(ABC):
    """
    Fictionalized external venue used as a reference for trading strategies.
    """

    @abstractmethod
    def prices(self, sim_assets: List[SimAsset], timestep: TimeStep) -> List[float]:
        """
        This particular signature supposes:
        - an infinite-depth external venue, i.e. we can trade at any size
          at the given price without market impact.
        - the "orderbook" is symmetric, i.e. trade direction doesn't matter.
        """
        raise NotImplementedError
