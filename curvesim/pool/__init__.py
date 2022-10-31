"""
Pool subpackage for creating Curve pool objects.

This subpackage can be used standalone from the simulation functionality
for interactive exploration of Curve pool behavior.

The two primary ways to create pools are `get` and `make`, which allow you
to create pools from on-chain state or passed-in parameters, respectively.

Pool calculations are thoroughly unit-tested against the corresponding
smart contract code.  We aim for the exact results as in the vyper
integer arithmetic.

The pool interfaces largely adhere to the smart contracts but in a few
cases allow an extra option, such as enabling fees.
"""

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
    """
    Factory function for creating pools from "raw" parameters, i.e. no
    data pulled from chain.

    Parameters
    ----------

    Returns
    -------
    :class:`Pool`
    """
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


def get(address_or_symbol, chain="mainnet", src="cg", balanced=(True, True)):
    """
    Parameters
    ----------
    address_or_symbol: str
        pool address prefixed with "0x" or LP token symbol

        .. warning::
            An LP token symbol need not be unique.  In particular, factory pools
            are deployed permissionlessly and no checks are done to ensure unique
            LP token symbol.  Currently the first pool retrieved from the subgraph
            is used; this is effectively random.
    chain: str
        chain/layer2 identifier, e.g. "mainnet", "arbitrum", "optimism"
    src: str
        data source identifier: "nomics", "cg", or "local"
    balances: (bool, bool)


    Returns
    -------
    :class:`Pool`

    Examples
    --------
    >>> import curvesim
    >>> pool = curvesim.pool.get("0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7", "mainnet")
    """
    p = _get_pool_data(address_or_symbol, chain=chain, src=src)
    return p.pool(balanced=balanced)
