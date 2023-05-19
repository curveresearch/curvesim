"""
Tools for retrieving price data.
Currently supports Coingecko, Nomics, and locally stored data.

To use nomics, set the OS environment variable NOMICS_API_KEY.

"""

from curvesim.exceptions import NetworkError

from .sources import coingecko, local


def get(coins, days=60, data_dir="data", src="coingecko", end=None):
    """
    Pull price and volume data for given coins.

    Data is returned for all pairwise combinations of the input coins.

    Parameters
    ----------
    coins : list of str
        List of coin addresses.

    days : int, default=60
        Number of days to pull data for.

    data_dir : str, default="data"
        Directory to load local data from.

    src : str, default="coingecko"
        Data source ("coingecko", "nomics", or "local").


    Returns
    -------
    prices : pandas.DataFrame
        Timestamped prices for each pair of coins.

    volumes : pandas.DataFrame
        Timestamped volumes for each pair of coins.

    pzero : int or pandas.Series
        Proportion of timestamps with zero volume.

    """
    if src == "coingecko":
        prices, volumes, pzero = coingecko(coins, days=days)

    elif src == "nomics":
        raise NetworkError("Nomics data is no longer supported.")

    elif src == "local":
        prices, volumes, pzero = local(coins, data_dir=data_dir, end=end)

    return prices, volumes, pzero
