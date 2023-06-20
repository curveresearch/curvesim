from abc import ABC, abstractmethod
from typing import Union

from curvesim.logging import get_logger
from curvesim.utils import dataclass

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Trade:
    """Data container for a trade to be executed."""

    coin_in: Union[str, int]
    coin_out: Union[str, int]
    amount_in: int

    def __iter__(self):
        # pylint: disable=no-member
        return (getattr(self, attr) for attr in self.__slots__)


@dataclass(slots=True)
class TradeResult:
    """Data container for a trade execution."""

    coin_in: Union[str, int]
    coin_out: Union[str, int]
    amount_in: int
    amount_out: int
    fee: int

    def __iter__(self):
        # pylint: disable=no-member
        return (getattr(self, attr) for attr in self.__slots__)

    def set_attrs(self, **kwargs):
        """Sets multiple attributes defined by keyword arguments."""
        for attr, value in kwargs.items():
            setattr(self, attr, value)

    @classmethod
    def from_trade(cls, trade, amount_out=None, fee=None):
        """Initializes a TradeResult object from a Trade object"""
        return cls(trade.coin_in, trade.coin_out, trade.amount_in, amount_out, fee)


class Trader(ABC):
    """
    Computes, executes, and reports out arbitrage trades.
    """

    def __init__(self, pool):
        """
        Parameters
        ----------
        pool :
            Simulation interface to a subclass of :class:`.Pool`.

        """
        self.pool = pool

    @abstractmethod
    def compute_trades(self, *args):
        """
        Computes trades to execute on the pool.

        Returns
        -------
        trades : list of :class:`Trade` objects
            List of trades to perform.

        additional_data: dict
            Dict of additional data to be passed to the state log as part of trade_data.
        """
        raise NotImplementedError

    def do_trades(self, trades):
        """
        Executes a series of trades.

        Parameters
        ----------
        trades : list of :class:`Trade` objects
            Trades to execute.

        Returns
        -------
        trades: list of :class:`TradeResult` objects
            The results of the trades.

        """

        trade_results = []
        for trade in trades:
            dy, fee = self.pool.trade(trade.coin_in, trade.coin_out, trade.amount_in)
            trade_results.append(TradeResult.from_trade(trade, amount_out=dy, fee=fee))

        return trade_results

    def process_time_sample(self, *args):
        """
        Process given tick data by computing and executing trades.

        The input args must be properly formed and fed by the
        parent `Strategy` object housing the trader class via its
        :meth:`~curvesim.pipelines.templates.Strategy._get_trader_inputs`.
        """
        trades, additional_data = self.compute_trades(*args)
        trade_results = self.do_trades(trades)

        return {"trades": trade_results, **additional_data}
