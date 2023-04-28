from numpy import array

from curvesim.exceptions import CurvesimValueError
from curvesim.logging import get_logger
from curvesim.network.subgraph import redemption_prices_sync as _redemption_prices
from curvesim.network.subgraph import volume_sync as _volume
from curvesim.pool.stableswap.metapool import CurveMetaPool
from curvesim.pool_data.metadata.base import PoolMetaDataInterface

from .metadata import PoolMetaData

logger = get_logger(__name__)


class PoolDataCache:
    """
    Container with methods to return pool state, metadata, and pools employing them.
    """

    def __init__(self, metadata_dict, cache_data=False, days=60):
        """
        Parameters
        ----------
        metadata_dict : dict, PoolMetaDataInterface
            Pool metadata in the format returned by network.subgraph.pool_snapshot.

        cache_data : bool, optional
            If True, fetches and caches historical volume and redemption price.

        days : int, default=60
            Number of days to pull data for if caching.

        """
        if isinstance(metadata_dict, dict):
            self.metadata = PoolMetaData(metadata_dict)
        elif isinstance(metadata_dict, PoolMetaDataInterface):
            self.metadata = metadata_dict
        else:
            raise CurvesimValueError(
                "Metadata must be of type dict or PoolMetaDataInterface."
            )
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
            logger.info("Getting cached historical volume...")
            return self._volume

        logger.info("Fetching historical volume...")
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
            logger.info("Getting cached redemption prices...")
            return self._redemption_prices

        address = self.metadata.address
        chain = self.metadata.chain

        r = _redemption_prices(address, chain, days=days, end=end)

        if store:
            self._redemption_prices = r

        return r
