"""
Utility functions for working with datetimes in UTC format.

This module provides custom versions of common datetime operations to ensure
returned datetimes are always in the UTC timezone and are not naive.

The main goal is to prevent potential issues related to timezone-aware and
timezone-naive datetime objects.

Recommended style for importing is:

    from curvesim.utils import datetime

    datetime.now()

This syntactically substitutes the `datetime.datetime` class methods with
this module's functions.
"""
from datetime import datetime, timezone


def now() -> datetime:
    """
    Customized version of `datetime.datetime.now` to ensure
    UTC timezone and format.

    Returns
    -------
    datetime
        Current UTC datetime with hour, minute, second, and microsecond set to 0.
        This datetime is timezone-aware and is not naive.
    """
    utc_dt = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return utc_dt


def fromtimestamp(timestamp: int) -> datetime:
    """
    Customized version of `datetime.datetime.fromtimestamp` to ensure
    UTC timezone and format.

    Parameters
    ----------
    timestamp : int
        Unix timestamp to be converted to datetime.

    Returns
    -------
    datetime
        The UTC datetime representation of the given timestamp.
        This datetime is timezone-aware and is not naive.
    """
    utc_timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return utc_timestamp
