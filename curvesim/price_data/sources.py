"""
Helper functions for the different data sources we pull from.
"""
from datetime import datetime, timezone

from curvesim.logging import get_logger
from curvesim.network import coingecko as _coingecko
from curvesim.network import nomics as _nomics

logger = get_logger(__name__)


def coingecko(coins, chain="mainnet", days=60, end=None):
    """
    Fetch CoinGecko price data for specified coins.

    Parameters
    ----------
    coins : list of str
        List of coin symbols to fetch data for.
    chain : str, optional
        Blockchain network to consider. Default is "mainnet".
    days : int, optional
        Number of past days to fetch data for. Default is 60.
    end : int, optional
        End timestamp for the data in seconds since epoch.
        If None, the end time will be the current time. Default is None.

    Returns
    -------
    tuple of (dict, dict, int)
        Tuple of prices, volumes, and pzero (fixed as 0 for this function).
    """
    logger.info("Fetching CoinGecko price data...")
    prices, volumes = _coingecko.pool_prices(coins, "usd", days, chain=chain, end=end)
    pzero = 0

    return prices, volumes, pzero


def local(coins, data_dir="data", end=None):
    """
    Load data for specified coins from a local directory.

    Parameters
    ----------
    coins : list of str
        List of coin symbols to load data for.
    data_dir : str, optional
        Path to the directory containing the data files. Default is "data".
    end : int, optional
        End timestamp for the data in seconds since epoch.
        If None, the end time will be the current time. Default is None.

    Returns
    -------
    tuple of (dict, dict, int)
        Tuple of prices, volumes, and pzero.
    """
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
