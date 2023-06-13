from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Union

from curvesim.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class Trade:
    coin_in: Union[str, int]
    coin_out: Union[str, int]
    amount_in: int

    def __iter__(self):
        return (getattr(self, attr) for attr in self.__slots__)


@dataclass(slots=True)
class TradeResult:
    coin_in: Union[str, int]
    coin_out: Union[str, int]
    amount_in: int
    amount_out: int
    fee: int

    def __iter__(self):
        return (getattr(self, attr) for attr in self.__slots__)


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
        trades : list of :class:`Trade` objects
            List of trades to perform.

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
        trades : list of :class:`Trade` objects
            Trades to execute.

        Returns
        -------
        trades_done: list of tuples
            Trades executed, formatted as (coin_in, coin_out, amount_in, amount_out).

        """

        trade_results = []
        for trade in trades:
            dy, fee, volume = self.pool.trade(*trade)
            trade_results.append(TradeResult(*trade, dy, fee))

        return trade_results

    def process_time_sample(self, *args):
        """
        Process given tick data by computing and executing trades.

        The input args must be properly formed and fed by the
        parent `Strategy` object housing the trader class via its
        :meth:`~curvesim.pipelines.templates.Strategy._get_trader_inputs`.
        """
        trades, _, _ = self.compute_trades(*args)
        trade_results = self.do_trades(trades)

        pool = self.pool
        pool_prices = {pair: pool.price(*pair) for pair in pool.assets.symbol_pairs}

        return {"trades": trade_results, "pool_prices": pool_prices}
