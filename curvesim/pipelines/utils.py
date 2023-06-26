"""Miscellaneous utility functions."""
from math import factorial

from numpy import append, array

from curvesim.logging import get_logger
from curvesim.pool import CurveMetaPool, CurvePool

logger = get_logger(__name__)


def compute_volume_multipliers(pool_vol, market_vol, n, pool_type, mode=1):
    """
    Computes volume multipliers (vol_mult) used for volume limiting.

    Parameters
    ----------
    pool_vol : float, int, or list
        Total volume for the pool over the simulation period.

    market_vol : dict
        Total market volume for each token pair over the simulation period.

    n : int
        The number of token-types in the pool (e.g., DAI, USDC, USDT = 3)

    pool_type : str
        "CurvePool" or "CurveMetaPool"

    vol_mode : int, default=1
        Modes for computing the volume multiplier:

        1: limits trade volumes proportionally to market volume for each pair

        2: limits trade volumes equally across pairs

        3: mode 2 for trades with meta-pool asset, mode 1 for basepool-only trades

    """
    pairs, market_vol = zip(*market_vol.items())
    pool_vol_array = array(pool_vol)
    market_vol_array = array(market_vol)

    try:
        get_vol_mult = _pool_functions[pool_type]
    except KeyError as e:
        raise TypeError(
            f"Pool type {pool_type} not supported by volume limiter."
        ) from e

    vol_mult = get_vol_mult(pool_vol_array, market_vol_array, n, mode)
    vol_mult_dict = dict(zip(pairs, vol_mult))

    logger.info(f"Volume Multipliers: {format_info_str(vol_mult_dict)}")
    return vol_mult_dict


def pool_vol_mult(pool_vol, market_vol, n, mode):
    if mode == 1:
        vol_mult = [pool_vol / market_vol.sum()] * n

    elif mode == 2:
        vol_mult = pool_vol.repeat(n) / n / market_vol

    elif mode == 3:
        logger.info("Vol_mode=3 only available for meta-pools. Reverting to vol_mode=1")
        vol_mult = [pool_vol / market_vol.sum()] * n

    else:
        raise ValueError(f"Mode must be integer 1, 2, or 3, not {mode}.")

    return vol_mult


def metapool_vol_mult(pool_vol, market_vol, n, mode):
    pool_vol_meta = pool_vol[0]
    pool_vol_base = pool_vol[1]
    mkt_vol_meta = market_vol[0 : n[1]]
    mkt_vol_base = market_vol[n[1] :]

    n_base_pairs = int(factorial(n[1]) / 2 * factorial(n[1] - 2))

    if mode == 1:
        vol_mult = append(
            pool_vol_meta / mkt_vol_meta.sum().repeat(n[1]),
            pool_vol_base / mkt_vol_base.sum().repeat(n_base_pairs),
        )

    elif mode == 2:
        vol_mult = append(
            pool_vol_meta.repeat(n[1]) / n[1] / mkt_vol_meta,
            pool_vol_base.repeat(n_base_pairs) / n_base_pairs / mkt_vol_base,
        )

    elif mode == 3:
        vol_mult = append(
            pool_vol_meta.repeat(n[1]) / n[1] / mkt_vol_meta,
            pool_vol_base / mkt_vol_base.sum().repeat(n_base_pairs),
        )

    else:
        raise ValueError(f"Mode must be integer 1, 2, or 3, not {mode}.")

    return vol_mult


def format_info_str(vol_mult_dict):
    info = [f"{base}/{quote}: {mult}" for (base, quote), mult in vol_mult_dict.items()]
    new_line = "\n    "
    return new_line + new_line.join(info)


_pool_functions = {CurvePool: pool_vol_mult, CurveMetaPool: metapool_vol_mult}
