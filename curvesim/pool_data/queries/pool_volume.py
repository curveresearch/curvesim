"""
Functions to get historical volume for Curve pools.
"""

from datetime import datetime
from math import comb
from typing import List, Tuple, Union

from pandas import DataFrame, Series

from curvesim.constants import Chain
from curvesim.logging import get_logger
from curvesim.network.curve_prices import get_pool_pair_volume_sync
from curvesim.pool_data.metadata import PoolMetaDataInterface
from curvesim.utils import get_event_loop, get_pairs

from .metadata import get_metadata

logger = get_logger(__name__)


def get_pool_volume(
    metadata_or_address: Union[PoolMetaDataInterface, str],
    start: Union[int, datetime],
    end: Union[int, datetime],
    chain: Union[str, Chain] = Chain.MAINNET,
) -> DataFrame:
    """
    Gets historical daily volume for each pair of coins traded in a Curve pool.

    Parameters
    ----------
    metadata_or_address: PoolMetaDataInterface or str
        Pool metadata or pool address to fetch metadata.

    start: datetime.datetime or int (POSIX timestamp)
        Timestamp of the last time to pull data for.

    end: datetime.datetime or int (POSIX timestamp)
        Timestamp of the last time to pull data for.

    chain: str, default "mainnet"
        Chain to use if pool address is provided to fetch metadata.

    Returns
    -------
    DataFrame
        Rows: DateTimeIndex, Columns: pairwise tuples of coin symbols

    """

    logger.info("Fetching historical pool volume...")

    if isinstance(metadata_or_address, str):
        pool_metadata: PoolMetaDataInterface = get_metadata(metadata_or_address, chain)
    else:
        pool_metadata = metadata_or_address

    pair_data = _get_pair_data(pool_metadata)
    start_ts, end_ts = _process_timestamps(start, end)
    loop = get_event_loop()

    volumes: dict[Tuple[str, str], Series] = {}
    for pool_address, pair_addresses, pair_symbols in pair_data:

        # to remove
        pair_addresses_0 = (
            "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
            if pair_addresses[0] == "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
            else pair_addresses[0]
        )
        pair_addresses_1 = pair_addresses[1]
        pair_addresses_to_use = (pair_addresses_0, pair_addresses_1)

        data: DataFrame = get_pool_pair_volume_sync(
            pool_address,
            *pair_addresses_to_use,
            start_ts,
            end_ts,
            chain=pool_metadata.chain,
            event_loop=loop,
        )
        volumes[pair_symbols] = data["volume"]

    volume_df = _make_volume_df(volumes)
    return volume_df


def _get_pair_data(pool_metadata) -> List[Tuple[str, Tuple[str, str], Tuple[str, str]]]:
    coin_addresses = _get_coin_addresses(pool_metadata)
    pair_symbols = get_pairs(pool_metadata.coin_names)
    pair_addresses = get_pairs(coin_addresses)

    if isinstance(pool_metadata.n, list):
        pool_addresses = _get_metapool_addresses(pool_metadata)
    else:
        pool_addresses = [pool_metadata.address] * comb(pool_metadata.n, 2)
    return list(zip(pool_addresses, pair_addresses, pair_symbols))


def _get_coin_addresses(pool_metadata) -> List[str]:
    # pylint: disable=protected-access
    if "wrapper" in pool_metadata._dict["coins"]:
        return pool_metadata._dict["coins"]["wrapper"]["addresses"]

    return pool_metadata.coins


def _get_metapool_addresses(pool_metadata) -> List[str]:
    n_meta = pool_metadata.n[0] - 1
    n_base = pool_metadata.n[1]
    address_meta = pool_metadata.address
    # pylint: disable-next=protected-access
    address_base = pool_metadata._dict["basepool"]["address"]

    n_pairs_meta = comb(n_meta, 2) + n_meta * n_base
    n_pairs_base = comb(n_base, 2)

    return [address_meta] * n_pairs_meta + [address_base] * n_pairs_base


def _process_timestamps(start, end) -> Tuple[int, int]:
    if isinstance(start, datetime):
        start = int(start.timestamp())

    if isinstance(end, datetime):
        end = int(end.timestamp())

    return start, end


def _make_volume_df(volumes) -> DataFrame:
    df = DataFrame(volumes)
    df.columns = df.columns.to_flat_index()
    logger.info("Days of volume returned:\n%s", df.count().to_string())
    df.fillna(0.0, inplace=True)
    return df
