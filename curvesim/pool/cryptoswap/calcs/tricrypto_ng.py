import time
from math import isqrt
from typing import List

from gmpy2 import mpz

from curvesim.exceptions import CalculationError, CryptoPoolError, CurvesimValueError
from curvesim.logging import get_logger
from curvesim.pool.base import Pool

logger = get_logger(__name__)

NOISE_FEE = 10**5  # 0.1 bps

MIN_GAMMA = 10**10
MAX_GAMMA = 2 * 10**16

EXP_PRECISION = 10**10

PRECISION = 10**18  # The precision to convert to
A_MULTIPLIER = 10000


def geometric_mean(unsorted_x: List[int], sort: bool) -> int:
    """
    (x[0] * x[1] * ...) ** (1/N)
    """
    n_coins: int = len(unsorted_x)
    x: List[int] = unsorted_x
    if sort:
        x = sorted(unsorted_x, reverse=True)

    D: int = mpz(x[0])
    diff: int = 0
    for _ in range(255):
        D_prev: int = D
        tmp: int = 10**18
        for _x in x:
            tmp = tmp * _x // D
        D = D * ((n_coins - 1) * 10**18 + tmp) // (n_coins * 10**18)
        diff = abs(D_prev - D)
        if diff <= 1 or diff * 10**18 < D:
            return int(D)
    raise CalculationError("Did not converge")


def lp_price(virtual_price, price_oracle) -> int:
    """
    Returns an LP token price approximating behavior as a constant-product AMM.
    """
    # TODO: find/implement integer cube root function
    # price_oracle = self.internal_price_oracle()
    # return (
    #     3 * self.virtual_price * icbrt(price_oracle[0] * price_oracle[1])
    # ) // 10**24
    raise CalculationError("LP price calc doesn't support more than 3 coins")
