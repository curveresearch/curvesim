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
    "get",
    "make",
    "Pool",
    "CurvePool",
    "CurveMetaPool",
    "CurveRaiPool",
    "CurveCryptoPool",
    "SimCurvePool",
    "SimCurveMetaPool",
    "SimCurveRaiPool",
]

from curvesim.exceptions import CurvesimValueError
from curvesim.logging import get_logger
from curvesim.pool_data import get_metadata
from curvesim.pool_data.metadata import PoolMetaData, PoolMetaDataInterface

from .base import Pool
from .cryptoswap import CurveCryptoPool
from .sim_interface import SimCurveMetaPool, SimCurvePool, SimCurveRaiPool
from .stableswap import CurveMetaPool, CurvePool, CurveRaiPool

logger = get_logger(__name__)


def make(
    A,
    D,
    n,
    *,
    basepool=None,
    rates=None,
    rate_multiplier=None,
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

    rates: list of int, optional
        precisions for each coin

    rate_multiplier: int, optional
        precision and rate adjustment for primary stable in metapool

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
    if rates and rate_multiplier:
        raise CurvesimValueError("Should have only `rates` or `rate_multiplier`.")

    if basepool:
        pool = CurveMetaPool(
            A,
            D,
            n,
            basepool,
            rate_multiplier=rate_multiplier,
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
            rates=rates,
            tokens=tokens,
            fee=fee,
            fee_mul=fee_mul,
            admin_fee=admin_fee,
        )

    return pool


def get_pool(
    pool_metadata,
    chain="mainnet",
    *,
    normalize=False,
    end_ts=None,
    env="prod",
):
    """
    Factory function for creating a pool based on metadata pulled from on-chain.

    Parameters
    ----------
    pool_metadata : Union[str, dict, PoolMetaDataInterface]
        pool address prefixed with "0x" or already pulled metadata in the form
        of a dict or :class:`PoolMetaDataInterface`.

    chain: str, default="mainnet"
        chain/layer2 identifier, e.g. "mainnet", "arbitrum", "optimism"

    normalize : bool, default=False
        If True, normalizes balances to 18 decimals (useful for sim calculations).

    end_ts: int, optional
        Posix timestamp indicating the datetime of the metadata snapshot.
        Only used when `pool_metadata` is an address.

    Returns
    -------
    :class:`Pool`

    Examples
    --------
    >>> import curvesim
    >>> pool_address = "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"
    >>> chain = "mainnet"
    >>> pool = curvesim.pool.get(pool_address, chain)
    """
    if end_ts and not isinstance(pool_metadata, str):
        raise CurvesimValueError("`end_ts` has no effect unless pool address is used.")

    if isinstance(pool_metadata, str):
        pool_metadata = get_metadata(pool_metadata, chain=chain, env=env, end_ts=end_ts)
    elif isinstance(pool_metadata, dict):
        pool_metadata = PoolMetaData(pool_metadata)

    if not isinstance(pool_metadata, PoolMetaDataInterface):
        raise CurvesimValueError(
            "`pool_metadata` must be of type `str`, `dict`, or `PoolMetaDataInterface`."
        )

    init_kwargs = pool_metadata.init_kwargs(normalize)
    logger.debug(init_kwargs)

    pool_type = pool_metadata.pool_type
    pool = pool_type(**init_kwargs)

    pool.metadata = pool_metadata._dict  # pylint: disable=protected-access

    return pool


POOL_TYPE_TO_CUSTOM_KWARGS = {SimCurveRaiPool: ["redemption_prices"]}


def get_sim_pool(
    pool_metadata,
    chain="mainnet",
    *,
    balanced=True,
    balanced_base=True,
    custom_kwargs=None,
    end_ts=None,
    env="prod",
):
    """
    Factory function for creating a sim pool based on metadata pulled from on-chain.

    Parameters
    ----------
    pool_metadata : Union[str, dict, PoolMetaDataInterface]
        pool address prefixed with "0x" or already pulled metadata in the form
        of a dict or :class:`PoolMetaDataInterface`.

    chain: str, default="mainnet"
        chain/layer2 identifier, e.g. "mainnet", "arbitrum", "optimism"

    balanced : bool, default=True
        If True, balances the pool value across assets.

    balanced_base : bool, default=True
        If True and pool is metapool, balances the basepool value across assets.

    end_ts: int, optional
        Posix timestamp indicating the datetime of the metadata snapshot.
        Only used when `pool_metadata` is an address.

    custom_kwargs: dict, optional
        Used for passing additional kwargs to the pool's `__init__`.

    Returns
    -------
    :class:`SimPool`

    Note
    -----
    The balances are always normalized to 18 decimals.

    Examples
    --------
    >>> import curvesim
    >>> pool_address = "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"
    >>> chain = "mainnet"
    >>> pool = curvesim.pool.get_sim_pool(pool_address, chain)
    """
    custom_kwargs = custom_kwargs or {}

    if end_ts and not isinstance(pool_metadata, str):
        raise CurvesimValueError("`end_ts` has no effect unless pool address is used.")

    if isinstance(pool_metadata, str):
        pool_metadata = get_metadata(pool_metadata, chain=chain, env=env, end_ts=end_ts)
    elif isinstance(pool_metadata, dict):
        pool_metadata = PoolMetaData(pool_metadata)

    if not isinstance(pool_metadata, PoolMetaDataInterface):
        raise CurvesimValueError(
            "`pool_metadata` must be of type `str`, `dict`, or `PoolMetaDataInterface`."
        )

    init_kwargs = pool_metadata.init_kwargs(normalize=True)
    logger.debug(init_kwargs)

    pool_type = pool_metadata.sim_pool_type

    custom_keys = POOL_TYPE_TO_CUSTOM_KWARGS.get(pool_type, [])
    for key in custom_keys:
        try:
            init_kwargs[key] = custom_kwargs.get(key)
        except KeyError as e:
            raise CurvesimValueError(f"'{pool_type.__name__}' needs '{key}'.") from e

    pool = pool_type(**init_kwargs)
    pool.metadata = pool_metadata._dict  # pylint: disable=protected-access
    _balance_pool(pool, balanced, balanced_base)

    return pool


def _balance_pool(pool, balanced, balanced_base):
    """
    Balances the pool and/or its basepool if applicable.

    Note: Mutates the `pool` argument.
    """
    # pylint: disable=protected-access
    if balanced:
        if callable(pool.D):
            # stableswap/metapool
            D = pool.D()
        else:
            # cryptopool
            D = pool.D
        pool.balances = pool._convert_D_to_balances(D)

    if balanced_base and hasattr(pool, "basepool"):
        basepool = pool.basepool
        D = basepool.D()
        basepool.balances = basepool._convert_D_to_balances(D)


get = get_pool
