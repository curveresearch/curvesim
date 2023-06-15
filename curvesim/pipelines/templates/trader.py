from abc import ABC, abstractmethod
from dataclasses import dataclass, FrozenInstanceError
from typing import Union

from curvesim.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class Trade:
    coin_in: Union[str, int] = None
    coin_out: Union[str, int] = None
    amount_in: int = None
    amount_out: int = None
    fee: int = None

    def __iter__(self):
        # pylint: disable=no-member
        return (getattr(self, attr) for attr in self.__slots__)

    def __setattr__(self, name, value):
        """
        Freezes attribute once it is changed from its default (None).
        Behavior modified from dataclass(Frozen=True).

        """
        if getattr(self, name, None) is not None:
            raise FrozenInstanceError(f"cannot assign to field {name}")

        super(Trade, self).__setattr__(name, value)

    def __delattr__(self, name):
        """
        Disables attribute deletion.

        """
        raise FrozenInstanceError(f"cannot delete field {name}")

    def set_attrs(self, **kwargs):
        """
        Sets multiple attributes defined by keyword arguments.
        """

        for attr, value in kwargs.items():
            setattr(self, attr, value)


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
        trades: list of :class:`Trade` objects
            The input trades with the resulting amount_out and fee attributes set.

        """

        for trade in trades:
            dy, fee = self.pool.trade(trade.coin_in, trade.coin_out, trade.amount_in)
            trade.set_attrs(amount_out=dy, fee=fee)

        return trades

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
