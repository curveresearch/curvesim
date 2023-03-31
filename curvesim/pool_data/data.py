from numpy import array

from curvesim.network.subgraph import redemption_prices_sync as _redemption_prices
from curvesim.network.subgraph import volume_sync as _volume
from curvesim.pool.stableswap.metapool import CurveMetaPool
from curvesim.pool.stableswap.raipool import CurveRaiPool

from .metadata import PoolMetaData


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
        self.volume(days=days, store=True, end=end)
        self.redemption_prices(days=days, store=True, end=end)

    def clear_cache(self):
        """
        Clears any cached data.
        """
        self._volume = None
        self._redemption_prices = None

    def pool(self, balanced=False, balanced_base=False, normalize=False, sim=False):
        """
        Constructs a pool object based on the stored data.

        Parameters
        ----------
        balanced : bool, default=True
            If True, balances the pool value across assets.

        balanced_base : bool, default=True
            If True and pool is metapool, balances the basepool value across assets.

        normalize : bool, default=True
            If True, normalizes balances to 18 decimals (useful for sim calculations).

        sim: bool, default=False
            If True, returns a `SimPool` version of the pool.

        Returns
        -------
        Pool
        """
        metadata = self.metadata
        kwargs = metadata.init_kwargs(balanced, balanced_base, normalize)
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
        return self.pool(balanced, balanced_base, normalize=True, sim=True)

    @property
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

    @property
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

    def volume(self, days=60, store=False, get_cache=True, end=None):
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

        if issubclass(self.metadata.pool_type, CurveMetaPool):
            # pylint: disable-next=protected-access
            basepool_address = self.metadata._dict["basepool"]["address"]
            addresses = [addresses, basepool_address]
            vol = _volume(addresses, chain, days=days, end=end)
            summed_vol = array([sum(v) for v in vol])
        else:
            vol = _volume(addresses, chain, days=days, end=end)
            summed_vol = array(sum(vol))

        if store:
            self._volume = summed_vol

        return summed_vol

    @property
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

    @property
    def type(self):
        """
        Returns the pool type.

        Returns
        -------
        str

        """
        return self.metadata.pool_type

    def redemption_prices(self, days=60, store=False, get_cache=True, end=None):
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

        r = _redemption_prices(address, chain, days=days, end=end)

        if store:
            self._redemption_prices = r

        return r
