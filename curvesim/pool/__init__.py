__all__ = ["get", "make", "Pool"]

from ..pool_data import get as _get_pool_data
from .pool import Pool


def make(A, D, n, p=None, tokens=None, fee=4 * 10**6, fee_mul=None, r=None):
    pool = Pool(A, D, n, p=None, tokens=None, fee=4 * 10**6, fee_mul=None, r=None)

    return pool


def get(address_or_symbol, chain="mainnet", src="cg", balanced=(True, True)):
    p = _get_pool_data(
        address_or_symbol,
        chain=chain,
        src=src,
        balanced=balanced,
    )

    A = [p["A"], p["A_base"]]
    fee = [p["fee"], p["fee_base"]]

    pool = make(
        A, p["D"], p["n"], tokens=p["tokens"], fee=fee, fee_mul=p["fee_mul"], r=p["r"]
    )

    return pool
