__all__ = ["get", "make", "MetaPool", "Pool"]

from curvesim.pool_data import get as _get_pool_data

from .metapool import MetaPool
from .pool import Pool


def make(
    A,
    D,
    n,
    basepool=None,
    p=None,
    tokens=None,
    fee=4 * 10**6,
    fee_mul=None,
    admin_fee=0 * 10**9,
    r=None,
):

    if basepool:
        pool = MetaPool(
            A,
            D,
            n,
            basepool,
            p=p,
            tokens=tokens,
            fee=fee,
            fee_mul=fee_mul,
            admin_fee=admin_fee,
            r=r,
        )

    else:
        pool = Pool(
            A,
            D,
            n,
            p=p,
            tokens=tokens,
            fee=fee,
            fee_mul=fee_mul,
            admin_fee=admin_fee,
            r=r,
        )

    return pool


def get(address_or_symbol, chain="mainnet", src="cg", balanced=(False, False)):
    p = _get_pool_data(address_or_symbol, chain=chain, src=src)

    return p.pool(balanced=balanced)
