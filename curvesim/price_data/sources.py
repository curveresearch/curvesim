from datetime import datetime, timedelta, timezone

from curvesim.logging import get_logger
from curvesim.network import coingecko as _coingecko
from curvesim.network import nomics as _nomics

logger = get_logger(__name__)


def nomics(coins, days=60, data_dir="data", end=None):
    if end is None:
        t_end = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        custom_suffix = ""
    else:
        t_end = datetime.fromtimestamp(end, tz=timezone.utc)
        custom_suffix = "-" + str(end)
    t_start = t_end - timedelta(days=days)

    logger.info("Fetching Nomics price data...")
    logger.info("Timerange: %s to %s" % (str(t_start), str(t_end)))

    _nomics.update(
        coins, None, t_start, t_end, data_dir=data_dir, custom_suffix=custom_suffix
    )
    prices, volumes, pzero = _nomics.pool_prices(
        coins, data_dir=data_dir, custom_suffix=custom_suffix
    )

    return prices, volumes, pzero


def coingecko(coins, days=60):
    logger.info("Fetching CoinGecko price data...")
    prices, volumes = _coingecko.pool_prices(coins, "usd", days)
    pzero = 0

    return prices, volumes, pzero


def local(coins, data_dir="data", end=None):
    logger.info("Using local data...")
    if end is not None:
        t_end = datetime.fromtimestamp(end, tz=timezone.utc)
        custom_suffix = "-" + str(end)
    else:
        t_end = None
        custom_suffix = ""
    prices, volumes, pzero = _nomics.local_pool_prices(
        coins, data_dir=data_dir, t_end=t_end, custom_suffix=custom_suffix
    )

    return prices, volumes, pzero
