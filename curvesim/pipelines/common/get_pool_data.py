"""
Contains convenience functions to get Curve sim pools and/or metadata.
"""

from datetime import datetime

from curvesim.exceptions import CurvesimTypeError
from curvesim.pool import get_sim_pool
from curvesim.pool_data import get_metadata
from curvesim.pool_data.metadata import PoolMetaDataInterface


def get_pool_data(metadata_or_address, chain, env, pool_ts):
    """
    Gets sim pool and (if needed) pool metadata.
    """
    pool_ts = _parse_timestamp(pool_ts)
    pool_metadata = _parse_metadata_or_address(metadata_or_address, chain, pool_ts)
    pool = get_sim_pool(pool_metadata, env=env)

    return pool, pool_metadata


def _parse_timestamp(timestamp):
    if not timestamp:
        return timestamp

    if isinstance(timestamp, datetime):
        timestamp = int(timestamp.timestamp())

    if not isinstance(timestamp, int):
        _type = type(timestamp).__name__
        raise CurvesimTypeError(f"'Pool_ts' must be 'int' or 'timestamp', not {_type}.")

    return timestamp


def _parse_metadata_or_address(metadata_or_address, chain, pool_ts):
    if isinstance(metadata_or_address, str):
        pool_metadata: PoolMetaDataInterface = get_metadata(
            metadata_or_address, chain, end_ts=pool_ts
        )

    elif isinstance(metadata_or_address, PoolMetaDataInterface):
        pool_metadata = metadata_or_address

    else:
        _type = type(metadata_or_address).__name__
        raise CurvesimTypeError(
            "'Metadata_or_address' must be 'PoolMetaDataInterface' or 'str',"
            f"not {_type}."
        )

    return pool_metadata
