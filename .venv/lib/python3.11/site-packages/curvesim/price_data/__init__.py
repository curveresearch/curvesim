"""
Tools for retrieving price data.
Currently supports Coingecko and locally stored data.

Note
-----
Nomics data is deprecated.
"""

from curvesim.exceptions import NetworkError

from .sources import coingecko


def get(
    coins,
    chain="mainnet",
    *,
    days=60,
    data_dir="data",
    src="coingecko",
    end=None,
):
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
        prices, volumes, pzero = coingecko(coins, chain=chain, days=days, end=end)

    elif src == "nomics":
        raise NetworkError("Nomics data is no longer supported.")

    elif src == "local":
        raise NetworkError("Local data currently not supported.")

    return prices, volumes, pzero
