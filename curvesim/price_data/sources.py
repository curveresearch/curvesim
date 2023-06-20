from datetime import datetime, timezone

from curvesim.logging import get_logger
from curvesim.network import coingecko as _coingecko
from curvesim.network import nomics as _nomics

logger = get_logger(__name__)


def coingecko(coins, chain="mainnet", days=60, end=None):
    logger.info("Fetching CoinGecko price data...")
    prices, volumes = _coingecko.pool_prices(coins, "usd", days, chain=chain, end=end)
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
