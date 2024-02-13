from abc import ABC, abstractmethod


class Log(ABC):
    @abstractmethod
    def update(self, **kwargs):
        """Updates log data with event data."""

    @abstractmethod
    def get_logs(self):
        """Returns the accumulated log data."""