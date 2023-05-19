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
    Container for fetching and caching historical volume and redemption price data.

    Deprecation warning: this will likely be removed in a future release.
    """

    def __init__(self, metadata_dict, cache_data=False, days=60, end=None):
        """
        Parameters
        ----------
        metadata_dict : dict, :class:`PoolMetaDataInterface`
            Pool metadata in the format returned by :func:`curvesim.network.subgraph.pool_snapshot`.

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

        self.days = days
        self.end = end

        self._cached_volume = None
        self._cached_redemption_prices = None

        if cache_data:
            self.set_cache()

    def set_cache(self):
        """
        Fetches and caches historical volume and redemption price data.

        Parameters
        ----------
        days : int, default=60
            number of days to pull data for
        """
        self._cached_volume = self._get_volume()
        self._cached_redemption_prices = self._get_redemption_prices()

    def clear_cache(self):
        """
        Clears any cached data.
        """
        self._cached_volume = None
        self._cached_redemption_prices = None

    @property
    def volume(self):
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
        if self._cached_volume is not None:
            logger.info("Getting cached historical volume...")
            return self._cached_volume

        return self._get_volume()

    def _get_volume(self):
        logger.info("Fetching historical volume...")
        addresses = self.metadata.address
        chain = self.metadata.chain
        days = self.days
        end = self.end

        if issubclass(self.metadata.pool_type, CurveMetaPool):
            # pylint: disable-next=protected-access
            basepool_address = self.metadata._dict["basepool"]["address"]
            addresses = [addresses, basepool_address]
            vol = _volume(addresses, chain, days=days, end=end)
            summed_vol = array([sum(v) for v in vol])
        else:
            vol = _volume(addresses, chain, days=days, end=end)
            summed_vol = array(sum(vol))

        return summed_vol

    @property
    def redemption_prices(self):
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
        if self._cached_redemption_prices is not None:
            logger.info("Getting cached redemption prices...")
            return self._cached_redemption_prices

        return self._get_redemption_prices()

    def _get_redemption_prices(self):
        address = self.metadata.address
        chain = self.metadata.chain

        days = self.days
        end = self.end

        r = _redemption_prices(address, chain, days=days, end=end)

        return r
