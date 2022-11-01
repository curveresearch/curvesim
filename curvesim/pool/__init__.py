__all__ = ["get", "make", "MetaPool", "Pool", "RaiPool"]

from curvesim.pool_data import get as _get_pool_data

from .stableswap import MetaPool, Pool, RaiPool


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
        )

    return pool


def get(address_or_symbol, chain="mainnet", src="cg", balanced=(False, False)):
    p = _get_pool_data(address_or_symbol, chain=chain, src=src)

    return p.pool(balanced=balanced)
