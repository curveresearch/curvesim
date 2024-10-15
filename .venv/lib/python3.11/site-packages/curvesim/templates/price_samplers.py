from abc import ABC, abstractmethod
from datetime import datetime

from curvesim.logging import get_logger
from curvesim.utils import dataclass

logger = get_logger(__name__)


@dataclass(slots=True)
class PriceSample:
    """
    Attributes
    -----------
    timestamp : datetime.datetime
        Timestamp for the current price/volume.
    prices : dict
        Price for each pairwise coin combination.
    """

    timestamp: datetime
    prices: dict


class PriceSampler(ABC):
    """
    An iterator that yields market data ticks, i.e. price or other data
    for each timestamp.
    """

    @abstractmethod
    def __iter__(self) -> PriceSample:
        """
        Yields
        -------
        class:`PriceSample`
        """
        raise NotImplementedError
