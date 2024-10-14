"""
Interfaces for DataSources, used to fetch asset data over time (e.g., price/volume).
"""

from abc import ABC, abstractmethod
from glob import glob
from os import extsep
from os.path import join, expanduser
from typing import Callable, Optional, List

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

    def __init__(self, files: str, read_function: Optional[Callable] = None):
        """
        Fetches asset data for a particular range of times.

        Parameters
        ----------
        directory: str, default="" TODO
            Directory to pull data from.
            comma-separated str

        read_function: Callable, optional
            Optional custom function to read data file.

        """

        """
        how to instantiate in get_price_data?
            map this type of str to DataSourceEnum.LOCAL = CsvDataSource somewhere
                if is str and is not in datasourceenum:
                    datasourceenum.local(files=str) -> inside FileDataSource, str.split by ",", apply expanduser, apply glob.glob, instantiate self.files as the glob result list (files type = List[str or pathlib.Path?], changed from dir = ""), create mapping from the names in files

                if is DataSourceEnum.LOCAL, filedatasource files arg default will be empty str (list?)? -> instantiate files as the result of searching all .csv in current dir -> the mapping (FileDataSource) will just be: result of fnmatching or globbing for files in files containing "{base}-{quote}" in the name (HOW TO KNOW THE SIMASSETS?), else (if empty) raise error
                OR JUST RAISE ERROR in get_price_data
        """
        if files == "":
            raise Exception("No empty")

        paths: List[str] = files.split(",")
        paths = [expanduser(path) for path in paths]
        full_paths: List[str] = []
        for path in paths:
            matches: List[str] = glob(path)
            if matches == []:
                raise OSError(f"supplied path doesn't exist {path}")
            if not matches[0].endswith(f"{extsep}{self.file_extension}"):
                raise Exception("wrong file type")
            full_paths.append(matches[0])

        self.filepaths: List[str] = full_paths

        #self.directory = directory
        self.read_function = read_function or self._default_read_function

    def query(
        self, sim_asset: OnChainAssetPair, time_sequence: TimeSequence
    ) -> DataFrame:
        """
        Fetches asset data for a particular range of times.
        Uses filepath: {base_symbol}-{quote_symbol}.{file_extension} TODO

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
        search_term = f"{sim_asset.base.symbol}-{sim_asset.quote.symbol}"
        try:
            filepath: str = list(filter(lambda filename: search_term in filename, self.filepaths)) [0]
        except IndexError:
            raise Exception(f"no file for {search_term}")
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
