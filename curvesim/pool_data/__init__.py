"""
Tools for fetching pool state and metadata.
Currently supports stableswap pools, meta-pools, and rebasing (RAI) metapools.
"""

__all__ = ["PoolData", "from_address", "from_symbol", "get"]

from numpy import array

from ..network.subgraph import redemption_prices_sync as _redemption_prices
from ..network.subgraph import volume_sync as _volume
from ..pool.stableswap import CurveMetaPool, CurvePool, CurveRaiPool
from .queries import from_address, from_symbol


def get(address_or_symbol, chain="mainnet"):
    """
    Pulls pool state and metadata from daily snapshot.

    Parameters
    ----------
    address_or_symbol : str
        Pool address prefixed with “0x” or LP token symbol.

    chain : str
        Chain/layer2 identifier, e.g. “mainnet”, “arbitrum”, “optimism".

    Returns
    -------
    PoolData

    """
    if address_or_symbol.startswith("0x"):
        from_x = from_address
    else:
        from_x = from_symbol

    params = from_x(address_or_symbol, chain)

    pool_data = PoolData(params)

    return pool_data


class PoolData:
    """
    Container with methods to return pool state, metadata, and pools employing them.
    """

    def __init__(self, metadata_dict, cache_data=False, days=60):
        """
        Parameters
        ----------
        metadata_dict : dict
            Pool metadata in the format returned by network.subgraph.pool_snapshot.

        cache_data : bool, optional
            If True, fetches and caches historical volume and redemption price.

        days : int, default=60
            Number of days to pull data for if caching.

        """
        self.dict = metadata_dict
        if cache_data:
            self.set_cache(days=days)

    def set_cache(self, days=60):
        """
        Fetches and caches historical volume and redemption price data.

        Parameters
        ----------
        days : int, default=60
            number of days to pull data for

        """
        self.volume(days=days, store=True)
        self.redemption_prices(store=True)

    def clear_cache(self):
        """
        Clears any cached data.

        """
        attrs = ["_volume", "_redemption_prices"]
        for attr in attrs:
            try:
                delattr(self, attr)
            except AttributeError:
                print(f"Cached {attr[1:]} already cleared")

    def pool(self, balanced=(True, True)):
        """
        Constructs a pool object based on the stored data.

        Parameters
        ----------
        balanced : tuple, default=(True,True)
            If True, balances the pool value across assets.

            The second element refers to the basepool, if present.

        Returns
        -------
        Pool

        """

        def bal(kwargs, balanced):
            reserves = kwargs.pop("reserves")
            if not balanced:
                kwargs.update({"D": reserves})
            return kwargs

        kwargs = bal(self.dict["init_kwargs"].copy(), balanced[0])

        if self.dict["basepool"]:
            bp_kwargs = self.dict["basepool"]["init_kwargs"].copy()
            bp_kwargs = bal(bp_kwargs, balanced[1])
            kwargs.update({"basepool": CurvePool(**bp_kwargs)})

            r = self.redemption_prices()
            if r is None:
                pool = CurveMetaPool(**kwargs)
            else:
                pool = CurveRaiPool(r, **kwargs)

        else:
            pool = CurvePool(**kwargs)

        pool.metadata = self.dict

        return pool

    def coins(self):
        """
        Returns coin addresses for the pool's holdings.

        For pools that are not on Ethereum mainnet, the address
        for the corresponding mainnet token is returned.

        For lending tokens (e.g., aTokens or cTokens), the
        address for the underlying token is returned.

        Returns
        -------
        list of strings
            coin addresses

        """
        if not self.dict["basepool"]:
            c = self.dict["coins"]["addresses"]
        else:
            c = (
                self.dict["coins"]["addresses"][:-1]
                + self.dict["basepool"]["coins"]["addresses"]
            )
        return c

    def coin_names(self):
        """
        Returns coin names for the pool's holdings.

        For pools that are not on Ethereum mainnet, the name
        of the corresponding mainnet token is returned.

        For lending tokens (e.g., aTokens or cTokens), the
        name of the underlying token is returned.

        Returns
        -------
        list of strings
            coin names

        """
        if not self.dict["basepool"]:
            c = self.dict["coins"]["names"]
        else:
            c = (
                self.dict["coins"]["names"][:-1]
                + self.dict["basepool"]["coins"]["names"]
            )
        return c

    def volume(self, days=60, store=False, get_cache=True):
        """
        Fetches the pool's historical volume over the specified number of days.

        Parameters
        ----------
        days : int, default=60
            Number of days to pull data for.

        store : bool, default=False
            If true, caches the fetched data.

        get_cache : bool, default=True
            If true, returns cached data when available.

        Returns
        -------
        numpy.ndarray
            Total volume summed across the specified number of days.

        """
        if get_cache and hasattr(self, "_volume"):
            print("Getting cached historical volume...")
            return self._volume

        print("Fetching historical volume...")
        addrs = self.dict["address"]
        chain = self.dict["chain"]

        if self.dict["basepool"]:
            addrs = [addrs, self.dict["basepool"]["address"]]
            vol = _volume(addrs, chain, days=days)
            summed_vol = array([sum(v) for v in vol])

        else:
            vol = _volume(addrs, chain, days=days)
            summed_vol = array(sum(vol))

        if store:
            self._volume = summed_vol

        return summed_vol

    def n(self):
        """
        Returns the number of token-types (e.g., DAI, USDC, USDT) in a pool.

        Returns
        -------
        int or list of ints
            Number of token-types.

            For metapools, a list [n_metapool, n_basepool] is returned.

            N_metapool includes the basepool LP token.

        """
        if not self.dict["basepool"]:
            n = self.dict["init_kwargs"]["n"]
        else:
            n = [
                self.dict["init_kwargs"]["n"],
                self.dict["basepool"]["init_kwargs"]["n"],
            ]

        return n

    def type(self):
        """
        Returns the pool type.

        Returns
        -------
        str

        """
        if self.dict["basepool"]:
            return CurveMetaPool
        else:
            return CurvePool

    def redemption_prices(self, days=60, store=False, get_cache=True):
        """
        Fetches the pool's redemption price over the specified number of days.

        Note: only returns data for RAI3CRV pool. Otherwise, returns None.

        Parameters
        ----------
        days : int, default=60
            Number of days to pull data for.

        store : bool, default=False
            If True, caches the fetched data.

        get_cache : bool, default=True
            If True, returns cached data when available.

        Returns
        -------
        pandas.DataFrame
            Timestamped redemption prices across the specified number of days.

        """
        if get_cache and hasattr(self, "_redemption_prices"):
            print("Getting cached redemption prices...")
            return self._redemption_prices

        address = self.dict["address"]
        chain = self.dict["chain"]

        r = _redemption_prices(address, chain, days=days)

        if store:
            self._redemption_prices = r

        return r
