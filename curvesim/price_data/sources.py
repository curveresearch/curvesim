from datetime import datetime, timedelta

from curvesim.network import coingecko as _coingecko
from curvesim.network import nomics as _nomics


def nomics(coins, days=60, data_dir="data"):
    t_end = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    t_start = t_end - timedelta(days=days)

    print("Fetching Nomics price data...")
    print("Timerange: %s to %s" % (str(t_start), str(t_end)))

    _nomics.update(coins, None, t_start, t_end, data_dir=data_dir)
    prices, volumes, pzero = _nomics.pool_prices(coins)

    return prices, volumes, pzero


def coingecko(coins, days=60):
    print("Fetching CoinGecko price data...")
    prices, volumes = _coingecko.pool_prices(coins, "usd", days)
    pzero = 0

    return prices, volumes, pzero


def local(coins, data_dir="data"):
    print("Using local data...")
    prices, volumes, pzero = _nomics.local_pool_prices(coins, data_dir=data_dir)

    return prices, volumes, pzero
