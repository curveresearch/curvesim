"""
Interfaces for DataSources, used to fetch asset data over time (e.g., price/volume).
"""

from abc import ABC, abstractmethod
from os import extsep
from os.path import join
from typing import Callable, Optional

from pandas import DataFrame

from .sim_asset import OnChainAssetPair
from .time_sequence import TimeSequence


class DataSource(ABC):
    """
    Abstract base class implementing the DataSource interface.
    """

    @abstractmethod
    def query(
        self, sim_asset: OnChainAssetPair, time_sequence: TimeSequence
    ) -> DataFrame:
        """
        Fetches asset data for a particular range of times.

        Parameters
        ----------
        sim_asset: OnChainAssetPair
            The asset-pair to pull data for.

        time_sequence: TimeSequence
            Timestamps to pull data for.

        Returns
        -------
        pandas.DataFrame
        """
        raise NotImplementedError


class ApiDataSource(DataSource):
    """
    DataSource that pulls data from a network API.
    """


class FileDataSource(DataSource):
    """
    DataSource that pulls data from local files.
    """

    def __init__(self, directory: str = "", read_function: Optional[Callable] = None):
        """
        Fetches asset data for a particular range of times.

        Parameters
        ----------
        directory: str, default=""
            Directory to pull data from.

        read_function: Callable, optional
            Optional custom function to read data file.

        """
        self.directory = directory
        self.read_function = read_function or self._default_read_function

    def query(
        self, sim_asset: OnChainAssetPair, time_sequence: TimeSequence
    ) -> DataFrame:
        """
        Fetches asset data for a particular range of times.
        Uses filepath: {directory}/{base_symbol}-{quote_symbol}.{file_extension}

        Parameters
        ----------
        sim_asset: OnChainAssetPair
            The asset-pair to pull data for.

        time_sequence: TimeSequence
            Timestamps to pull data for.

        Returns
        -------
        pandas.DataFrame
        """
        filename = sim_asset.base.symbol + "-" + sim_asset.quote.symbol
        filepath = join(self.directory, filename + extsep + self.file_extension)
        df = self.read_function(filepath, sim_asset, time_sequence)
        return df

    @property
    def file_extension(self):
        """
        The file extension used when loading data.
        """
        raise NotImplementedError

    def _default_read_function(
        self, filepath: str, sim_asset: OnChainAssetPair, time_sequence: TimeSequence
    ):
        """
        The default read function used by the DataSource.
        """
        raise NotImplementedError
