__all__ = ["get", "make", "MetaPool", "Pool"]

from curvesim.pool_data import get as _get_pool_data

from .metapool import MetaPool
from .pool import Pool


def get(address_or_symbol, chain="mainnet", src="cg", balanced=(False, False)):
    p = _get_pool_data(
        address_or_symbol,
        chain=chain,
        src=src,
        balanced=balanced,
    )

    return p.pool()
