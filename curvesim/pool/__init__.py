__all__ = ["get", "make", "MetaPool", "Pool"]

from curvesim.pool_data import get as _get_pool_data

from .metapool import MetaPool
from .pool import Pool

make = Pool


def get(address_or_symbol, chain="mainnet", src="cg", balanced=(True, True)):
    p = _get_pool_data(
        address_or_symbol,
        chain=chain,
        src=src,
        balanced=balanced,
    )

    if p["A_base"]:
        A = [p["A"], p["A_base"]]
        fee = [p["fee"], p["fee_base"]]
    else:
        A = p["A"]
        fee = p["fee"]

    pool = make(
        A, p["D"], p["n"], tokens=p["tokens"], fee=fee, fee_mul=p["fee_mul"], r=p["r"]
    )

    return pool
