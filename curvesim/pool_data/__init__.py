"""
Tools for fetching pool state and metadata.
Currently supports stableswap pools, meta-pools, and rebasing (RAI) metapools.
"""

__all__ = ["PoolData", "from_address", "from_symbol", "get"]

from numpy import array

from curvesim.exceptions import CurvesimException

from ..network.subgraph import has_redemption_prices
from ..network.subgraph import redemption_prices_sync as _redemption_prices
from ..network.subgraph import volume_sync as _volume
from ..pool.sim_interface import SimCurveMetaPool, SimCurvePool, SimCurveRaiPool
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
    # TODO: validate function arguments
    if address_or_symbol.startswith("0x"):
        from_x = from_address
    else:
        from_x = from_symbol

    params = from_x(address_or_symbol, chain)

    pool_data = PoolData(params)
    print("Pool data params:", params)

    return pool_data


class PoolMetaData:
    def __init__(self, metadata_dict):
        self._dict = metadata_dict

    def init_kwargs(self, balanced=True, balanced_base=True):
        def bal(kwargs, balanced):
            reserves = kwargs.pop("reserves")
            if not balanced:
                kwargs["D"] = reserves
            return kwargs

        kwargs = self._dict["init_kwargs"].copy()
        kwargs = bal(kwargs, balanced)

        if self._dict["basepool"]:
            bp_kwargs = self._dict["basepool"]["init_kwargs"].copy()
            bp_kwargs = bal(bp_kwargs, balanced_base)
            basepool = CurvePool(**bp_kwargs)
            basepool.metadata = self._dict["basepool"]
            kwargs["basepool"] = basepool

        return kwargs

    @property
    def address(self):
        return self._dict["address"]

    @property
    def chain(self):
        return self._dict["chain"]

    @property
    def has_redemption_prices(self):
        address = self.address
        chain = self.chain
        return has_redemption_prices(address, chain)

    @property
    def pool_type(self):
        if self._dict["basepool"]:
            if self.has_redemption_prices:
                _pool_type = CurveRaiPool
            else:
                _pool_type = CurveMetaPool
        else:
            _pool_type = CurvePool
        return _pool_type

    @property
    def sim_pool_type(self):
        pool_type = self.pool_type
        if pool_type == CurvePool:
            return SimCurvePool
        elif pool_type == CurveMetaPool:
            return SimCurveMetaPool
        elif pool_type == CurveRaiPool:
            return SimCurveRaiPool
        else:
            raise CurvesimException(f"No sim pool type for this pool type: {pool_type}")

    @property
    def coins(self):
        if not self._dict["basepool"]:
            c = self._dict["coins"]["addresses"]
        else:
            c = (
                self._dict["coins"]["addresses"][:-1]
                + self._dict["basepool"]["coins"]["addresses"]
            )
        return c

    @property
    def coin_names(self):
        if not self._dict["basepool"]:
            c = self._dict["coins"]["names"]
        else:
            c = (
                self._dict["coins"]["names"][:-1]
                + self._dict["basepool"]["coins"]["names"]
            )
        return c

    @property
    def n(self):
        if not self._dict["basepool"]:
            n = self._dict["init_kwargs"]["n"]
        else:
            n = [
                self._dict["init_kwargs"]["n"],
                self._dict["basepool"]["init_kwargs"]["n"],
            ]

        return n


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
        self.metadata = PoolMetaData(metadata_dict)
        self._volume = None
        self._redemption_prices = None

        if cache_data:
            self.set_cache(days=days)

    def set_cache(self, days=60, end=None):
        """
        Fetches and caches historical volume and redemption price data.

        Parameters
        ----------
        days : int, default=60
            number of days to pull data for
        """
        self.volume(days=days, store=True, end=None)
        self.redemption_prices(store=True, end=None)

    def clear_cache(self):
        """
        Clears any cached data.
        """
        self._volume = None
        self._redemption_prices = None

    def pool(self, balanced=True, balanced_base=True, sim=False):
        """
        Constructs a pool object based on the stored data.

        Parameters
        ----------
        balanced : bool, default=True
            If True, balances the pool value across assets.

        balanced_base : bool, default=True
            If True and pool is metapool, balances the basepool value across assets.

        sim: bool, default=False
            If True, returns a `SimPool` version of the pool.

        Returns
        -------
        Pool
        """
        metadata = self.metadata
        kwargs = metadata.init_kwargs(balanced, balanced_base)
        if sim:
            pool_type = metadata.sim_pool_type
        else:
            pool_type = metadata.pool_type

        if issubclass(pool_type, CurveRaiPool):
            r = self.redemption_prices()
            pool = pool_type(r, **kwargs)
        else:
            pool = pool_type(**kwargs)

        pool.metadata = metadata._dict  # pylint: disable=protected-access

        return pool

    def sim_pool(self, balanced=True, balanced_base=True):
        """
        Effectively the same as the `pool` method but returns
        an object in the `SimPool` hierarchy.
        """
        return self.pool(balanced, balanced_base, sim=True)

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
        return self.metadata.coins

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
        return self.metadata.coin_names

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
        if get_cache and self._volume is not None:
            print("Getting cached historical volume...")
            return self._volume

        print("Fetching historical volume...")
        addresses = self.metadata.address
        chain = self.metadata.chain

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
        return self.metadata.n

    def type(self):
        """
        Returns the pool type.

        Returns
        -------
        str

        """
        return self.metadata.pool_type

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
        if get_cache and self._redemption_prices is not None:
            print("Getting cached redemption prices...")
            return self._redemption_prices

        address = self.metadata.address
        chain = self.metadata.chain

        r = _redemption_prices(address, chain, days=days)

        if store:
            self._redemption_prices = r

        return r
