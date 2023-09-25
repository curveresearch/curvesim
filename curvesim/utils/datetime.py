from datetime import datetime, timezone


def now():
    """
    Customized version of `datetime.datetime.now` to ensure
    UTC timezone and format.
    """
    utc_dt = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return utc_dt


def fromtimestamp(timestamp):
    """
    Customized version of `datetime.datetime.fromtimestamp` to ensure
    UTC timezone and format.
    """
    utc_timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return utc_timestamp
