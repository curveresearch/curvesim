"""Contains data sources used by curvesim.price_data.get_price_data()"""

from enum import Enum

from .coingecko import CoinGeckoPriceVolumeSource
from .local import CsvDataSource


class DataSourceEnum(Enum):
    """
    Enum of data sources used by curvesim.price_data.get_price_data()
    """

    COINGECKO = CoinGeckoPriceVolumeSource
    LOCAL = CsvDataSource
