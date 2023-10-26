"""
Functions to get historical volume for Curve pools.
"""

from datetime import datetime, timezone
from math import comb
from typing import List, Optional, Tuple

from pandas import DataFrame, Series

from curvesim.logging import get_logger
from curvesim.network.curve_prices import get_pool_pair_volume_sync
from curvesim.pool_data.metadata import PoolMetaDataInterface
from curvesim.utils import get_event_loop, get_pairs

logger = get_logger(__name__)


def get_pool_volume(
    pool_metadata: PoolMetaDataInterface,
    days: int = 60,
    end: Optional[int] = None,
) -> DataFrame:
    """
    Gets historical daily volume for each pair of coins traded in a Curve pool.

    Parameters
    ----------
    pool_metadata: PoolMetaDataInterface
        Pool metadata for the pool of interest.

    days: int, defaults to 60
        Number of days to pull volume data for.

    end: int, defaults to start of current date
        Posix timestamp of the last time to pull data for.

    Returns
    -------
    DataFrame
        Rows: DateTimeIndex, Columns: pairwise tuples of coin symbols

    """

    logger.info("Fetching historical pool volume...")

    pair_data = _get_pair_data(pool_metadata)
    start_ts, end_ts = _process_timestamps(days, end)
    loop = get_event_loop()

    volumes: dict[Tuple[str, str], Series] = {}
    for pool_address, pair_addresses, pair_symbols in pair_data:
        data: DataFrame = get_pool_pair_volume_sync(
            pool_address,
            *pair_addresses,
            start_ts,
            end_ts,
            chain=pool_metadata.chain,
            event_loop=loop,
        )
        volumes[pair_symbols] = data["volume"]

    volume_df = _make_volume_df(volumes, days)
    return volume_df


def _get_pair_data(pool_metadata) -> List[Tuple[str, Tuple[str, str], Tuple[str, str]]]:
    pair_symbols = get_pairs(pool_metadata.coin_names)
    pair_addresses = get_pairs(pool_metadata.coins)

    if isinstance(pool_metadata.n, list):
        pool_addresses = _get_metapool_addresses(pool_metadata)
    else:
        pool_addresses = [pool_metadata.address] * comb(pool_metadata.n, 2)
    return list(zip(pool_addresses, pair_addresses, pair_symbols))


def _get_metapool_addresses(pool_metadata) -> List[str]:
    n_meta = pool_metadata.n[0] - 1
    n_base = pool_metadata.n[1]
    address_meta = pool_metadata.address
    # pylint: disable-next=protected-access
    address_base = pool_metadata._dict["basepool"]["address"]

    n_pairs_meta = comb(n_meta, 2) + n_meta * n_base
    n_pairs_base = comb(n_base, 2)

    return [address_meta] * n_pairs_meta + [address_base] * n_pairs_base


def _process_timestamps(days, end) -> Tuple[int, int]:
    end = end or int(
        datetime.now(timezone.utc)
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .timestamp()
    )
    start = end - days * 86400
    return start, end


def _make_volume_df(volumes, days) -> DataFrame:
    df = DataFrame(volumes)
    df.columns = df.columns.to_flat_index()
    if len(df) > days:
        df = df[-days:]
    logger.info("Days of volume returned:\n%s", df.count().to_string())
    df.fillna(0, inplace=True)
    return df
