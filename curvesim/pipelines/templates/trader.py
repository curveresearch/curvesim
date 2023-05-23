from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Union

from numpy import ndarray
from pandas import Series

from curvesim.logging import get_logger

logger = get_logger(__name__)


@dataclass(eq=False, slots=True)
class TradeData:
    trades: list
    volume: int
    price_errors: Union[list, ndarray, Series]


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
        Computes trades to optimally arbitrage the pool, constrained by volume limits.

        Returns
        -------
        trades : list of tuples
            List of trades to perform.
            Trades are formatted as (coin_in, coin_out, trade_size).

        errors : numpy.ndarray
            Post-trade price error between pool price and market price.

        res : scipy.optimize.OptimizeResult
            Results object from the numerical optimizer.

        """
        raise NotImplementedError

    def do_trades(self, trades):
        """
        Executes a series of trades.

        Parameters
        ----------
        trades : list of tuples
            Trades to execute, formatted as (coin_in, coin_out, trade_size).

        Returns
        -------
        trades_done: list of tuples
            Trades executed, formatted as (coin_in, coin_out, amount_in, amount_out).

        volume : int
            Total volume of trades in 18 decimal precision.

        """
        if len(trades) == 0:
            return [], 0

        total_volume = 0
        trades_done = []
        for trade in trades:
            i, j, dx = trade
            dy, fee, volume = self.pool.trade(i, j, dx)
            trades_done.append((i, j, dx, dy, fee))

            total_volume += volume

        return trades_done, total_volume

    def process_time_sample(self, *args):
        """
        Process given tick data by computing and executing trades.

        The input args must be properly formed and fed by the
        parent `Strategy` object housing the trader class via its
        :meth:`~curvesim.pipelines.templates.Strategy._get_trader_inputs`.
        """
        trades, price_errors, _ = self.compute_trades(*args)
        trades_done, volume = self.do_trades(trades)
        return TradeData(trades_done, volume, price_errors)
