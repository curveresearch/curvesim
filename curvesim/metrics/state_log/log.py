"""
Module to house the `StateLog`, a generic class to record changing pool states
during simulations.
"""
import gin

from pandas import DataFrame

from curvesim.templates import Log
from curvesim.utils import override

from .pool_parameters import get_pool_parameters
from .pool_state import get_pool_state


@gin.register
class StateLog(Log):
    """
    Logger that records simulation/pool state throughout each simulation run and
    computes metrics at the end of each run. TODO: CHANGE LATER
    """

    __slots__ = [
        "state_per_run",
        "state_per_trade",
    ]

    def __init__(self, pool):
        """
        TODO
        pool : SimPool 
        """
        # TODO: config the func with gin?
        self.state_per_run = get_pool_parameters(pool)
        self.state_per_trade = []

    @override
    def update(self, **kwargs):
        """Records pool state and any keyword arguments provided."""
        state: dict = {}

        if "pool" in kwargs:
            pool = kwargs.pop("pool") # Simpool type
            state["pool_state"] = get_pool_state(pool)

        state.update(kwargs)

        self.state_per_trade.append(state)

    @override
    def get_logs(self):
        """Returns the accumulated log data."""

        df = DataFrame(self.state_per_trade)

        times = [state["price_sample"].timestamp for state in self.state_per_trade]
        state_per_trade = {col: DataFrame(df[col].to_list(), index=times) for col in df}

        return {
            "pool_parameters": DataFrame(self.state_per_run, index=[0]),
            **state_per_trade,
        }
