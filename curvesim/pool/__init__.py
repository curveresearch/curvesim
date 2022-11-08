"""
Pool subpackage for creating Curve pool objects.

This subpackage can be used standalone from the simulation functionality
for interactive exploration of Curve pool behavior. The two primary ways to create
pools are `get` and `make`, which allow you to create pools from on-chain state or p
assed-in parameters, respectively.

Pool calculations are thoroughly unit-tested against the corresponding
smart contract code.  We aim for the exact results as in the vyper
integer arithmetic. The pool interfaces largely adhere to the smart contracts
but in a few cases allow an extra option, such as enabling/disabling fees.
"""

__all__ = [
    "Pool",
    "get",
    "make",
    "CurvePool",
    "CurveMetaPool",
    "CurveRaiPool",
]

from curvesim.pool_data import get as _get_pool_data

from .base import Pool
from .stableswap import CurveMetaPool, CurvePool, CurveRaiPool


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
    A: int
        Amplification coefficient.  This controls the curvature of the
        stableswap bonding curve.  Increased values makes the curve
        flatter in a greater neighborhood of equal balances.

        Defaults to [int(2 ** (a / 2)) for a in range(12, 28)].

    D: int
        Total pool liquidity given in 18 decimal precision.

    n: int
        The number of token-types in the pool (e.g., DAI, USDC, USDT = 3)

    basepool: dict, optional
        a dict cointaining the arguments for instantiating a basepool

    p: list of int, optional
        precisions for each coin

    tokens: int, optional
        Total LP token supply.

        .. note::
            The number of tokens does not influence "normal" pool computations;
            but, for metapools, the number of basepool tokens is critically
            important to trade calculations.

    fee: int
        Fees taken for both liquidity providers and the DAO.

        Units are in fixed-point so that 10**10 is 100%,
        e.g. 4 * 10**6 is 4 bps and 2 * 10**8 is 2%.

    fee_mul : int
        fee multiplier for dynamic fee pools

    admin_fee : int, default=0 * 10**9
        Fees taken for the DAO.  For factory pools, it is half of the total fees,
        as was typical for previous non-factory pools.

        Units are fixed-point percentage of `fee`, e.g. 5 * 10**9 is
        50% of the total fees.

    Returns
    -------
    :class:`Pool`
    """
    if basepool:
        pool = CurveMetaPool(
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
        pool = CurvePool(
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


def get(address_or_symbol, chain="mainnet", balanced=(False, False)):
    """
    Parameters
    ----------
    address_or_symbol: str
        pool address prefixed with "0x" or LP token symbol

        .. warning::
            An LP token symbol need not be unique.  In particular, factory pools
            are deployed permissionlessly and no checks are done to ensure unique
            LP token symbol.  Currently the first pool retrieved from the subgraph
            is used, which can be effectively random if token symbols clash.

    chain: str, default="mainnet"
        chain/layer2 identifier, e.g. "mainnet", "arbitrum", "optimism"

    balanced : tuple, default=(True,True)
            If True, balances the pool value across assets.

            The second element refers to the basepool, if present.


    Returns
    -------
    :class:`Pool`

    Examples
    --------
    >>> import curvesim
    >>> pool = curvesim.pool.get("0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7", "mainnet")
    """
    p = _get_pool_data(address_or_symbol, chain=chain)
    return p.pool(balanced=balanced)
