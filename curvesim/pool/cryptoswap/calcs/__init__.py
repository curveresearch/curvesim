"""
Pure calculations with a common interface to wrap around
differing calculations for 2 or coins.
"""
__all__ = [
    "geometric_mean",
    "newton_D",
    "get_y",
    "get_alpha",
    "get_p",
    "halfpow",
]
from math import ceil
from typing import List

from gmpy2 import mpz

from curvesim.exceptions import CalculationError, CurvesimValueError
from curvesim.logging import get_logger

from . import factory_2_coin, tricrypto_ng
from .tricrypto_ng import get_p

EXP_PRECISION = 10**10

logger = get_logger(__name__)


def geometric_mean(unsorted_x: List[int]) -> int:
    """
    (x[0] * x[1] * ...) ** (1/N)
    """
    n_coins = len(unsorted_x)
    if n_coins == 2:
        mean = factory_2_coin.geometric_mean(unsorted_x, True)
    elif n_coins == 3:
        mean = tricrypto_ng.geometric_mean(unsorted_x)
    else:
        raise CurvesimValueError("More than 3 coins is not supported.")

    return mean


def newton_D(A: int, gamma: int, xp: List[int], K0_prev: int = 0) -> int:
    """
    Compute D using using specific approaches depending on
    the number of coins.

    For 3 coins, we actually use Halley's method and allow a
    starting value.
    """
    n_coins = len(xp)
    if n_coins == 2:
        D = factory_2_coin.newton_D(A, gamma, xp)
    elif n_coins == 3:
        D = tricrypto_ng.newton_D(A, gamma, xp, K0_prev)
    else:
        raise CurvesimValueError("More than 3 coins is not supported.")

    return D


def get_y(A: int, gamma: int, xp: List[int], D: int, j: int) -> List[int]:
    """
    Compute an xp[j] that satisfies the Cryptoswap invariant.

    newton_y (for n = 2) and get_y (for n = 3) results may differ by
    2 wei or so as their computational approaches are vastly different.
    """
    n_coins: int = len(xp)
    if n_coins == 2:
        y_out: List[int] = [factory_2_coin.newton_y(A, gamma, xp, D, j), 0]
    elif n_coins == 3:
        y_out = tricrypto_ng.get_y(A, gamma, xp, D, j)
    else:
        raise CurvesimValueError("More than 3 coins is not supported.")

    return y_out


def get_alpha(
    ma_half_time: int, block_timestamp: int, last_prices_timestamp: int, n_coins: int
) -> int:
    if n_coins == 2:
        alpha: int = halfpow(
            (block_timestamp - last_prices_timestamp) * 10**18 // ma_half_time
        )
    elif n_coins == 3:
        # tricrypto-ng stores the ma half-time divided by ln(2), so we have to
        # take the real half-time and divide by ln(2) to use in the alpha calc.
        #
        # Note ln(2) = 0.693147... but the approx actually used is 694 / 1000.
        #
        # CAUTION: need to be wary of off-by-one errors from integer division.
        ma_half_time = ceil(ma_half_time * 1000 / 694)
        alpha = tricrypto_ng.wad_exp(
            -1 * ((block_timestamp - last_prices_timestamp) * 10**18 // ma_half_time)
        )
    else:
        raise CurvesimValueError("More than 3 coins is not supported.")

    return alpha


def halfpow(power: int) -> int:
    """
    1e18 * 0.5 ** (power/1e18)

    Inspired by:
    https://github.com/balancer-labs/balancer-core/blob/master/contracts/BNum.sol#L128
    """
    intpow: int = power // 10**18
    otherpow: int = power - intpow * 10**18
    if intpow > 59:
        return 0
    result: int = 10**18 // (2**intpow)
    if otherpow == 0:
        return result

    term: int = mpz(10**18)
    x: int = 5 * 10**17
    S: int = 10**18
    neg: bool = False

    for i in range(1, 256):
        K: int = i * 10**18
        c: int = K - 10**18
        if otherpow > c:
            c = otherpow - c
            neg = not neg
        else:
            c -= otherpow
        term = term * (c * x // 10**18) // K
        if neg:
            S -= term
        else:
            S += term
        if term < EXP_PRECISION:
            return int(result * S // 10**18)

    raise CalculationError("Did not converge")
