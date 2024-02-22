"""
Contains convenience functions for fetching asset price/volume data.
"""
from datetime import datetime, timedelta, timezone

from curvesim.pool_data import get_pool_assets
from curvesim.price_data import get_price_data
from curvesim.templates import DateTimeSequence


def get_asset_data(pool_metadata, time_sequence, data_source):
    """
    Fetches price/volume data for a pool's assets.
    """
    sim_assets = get_pool_assets(pool_metadata)
    time_sequence = time_sequence or _make_default_time_sequence()
    asset_data = get_price_data(sim_assets, time_sequence, data_source=data_source)
    return asset_data, time_sequence


def _make_default_time_sequence():
    t_end = datetime.now(timezone.utc) - timedelta(days=1)
    t_end = t_end.replace(hour=23, minute=0, second=0, microsecond=0)
    t_start = t_end - timedelta(days=60) + timedelta(hours=1)
    time_sequence = DateTimeSequence.from_range(start=t_start, end=t_end, freq="1h")
    return time_sequence
