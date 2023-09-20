from abc import ABC, abstractmethod


class Log(ABC):
    @abstractmethod
    def update(self, **kwargs):
        """Updates log data with event data."""

    @abstractmethod
    def compute_metrics(self):
        """Computes metrics from the accumulated log data."""
