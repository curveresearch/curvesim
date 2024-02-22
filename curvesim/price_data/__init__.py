"""
Tools for retrieving price data.
Currently supports Coingecko and locally stored data.

Note
-----
Nomics data is deprecated.
"""


from typing import List, Union

from pandas import concat

from curvesim.exceptions import CurvesimTypeError
from curvesim.templates import DataSource, SimAsset, TimeSequence

from .data_sources import DataSourceEnum


def get_price_data(
    sim_assets: List[SimAsset],
    time_sequence: TimeSequence,
    data_source: Union[str, DataSource, DataSourceEnum] = DataSourceEnum.COINGECKO,
):
    """
    Pull price and volume data for each sim_asset.


    Parameters
    ----------
    sim_assets: List[SimAsset]
        The assets to pull data for.

    time_sequence: TimeSequence
        Timestamps to pull data for. If the specified source can't provide data for
        the specified times, the data will be resampled.

    data_source: str, DataSource, or DataSourceEnum
        DataSource object to query.

    Returns
    -------
    pandas.DataFrame

    """

    data_source_instance = _instantiate_data_source(data_source)

    data = []
    for sim_asset in sim_assets:
        _data = data_source_instance.query(sim_asset, time_sequence)
        data.append(_data)

    df = concat(data, axis=1)
    return df


def _instantiate_data_source(data_source):
    if isinstance(data_source, str):
        data_source_instance = DataSourceEnum[data_source.upper()].value()

    elif isinstance(data_source, DataSourceEnum):
        data_source_instance = data_source.value()

    elif isinstance(data_source, DataSource):
        data_source_instance = data_source

    elif issubclass(data_source, DataSource):
        data_source_instance = data_source()

    else:
        raise CurvesimTypeError(
            "'data_source' must be str, DataSourceEnum, or DataSource subclass/instance"
        )

    return data_source_instance
