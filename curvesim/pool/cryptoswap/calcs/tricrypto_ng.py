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


def get_p(
    xp: List[int],
    D: int,
    A: int,
    gamma: int,
) -> List[int]:
    """
    @notice Calculates dx/dy.
    @dev Output needs to be multiplied with price_scale to get the actual value.
    @param _xp Balances of the pool.
    @param _D Current value of D.
    @param _A_gamma Amplification coefficient and gamma.
    """
    assert 10**17 <= D <= 10**15 * 10**18

    N = len(xp)

    # K0 = P * N**N / D**N.
    # K0 is dimensionless and has 10**36 precision:
    K0: int = N**N * xp[0] * xp[1] // D * xp[2] // D * 10**36 // D

    # GK0 is in 10**36 precision and is dimensionless.
    # GK0 = (
    #     2 * K0 * K0 / 10**36 * K0 / 10**36
    #     + (gamma + 10**18)**2
    #     - (K0 * K0 / 10**36 * (2 * gamma + 3 * 10**18) / 10**18)
    # )
    # GK0 is always positive. So the following should never revert:
    GK0: int = (
        2 * K0**2 // 10**36 * K0 // 10**36
        + (gamma + 10**18) ** 2
        - (K0**2 // 10**36 * (2 * gamma + 3 * 10**18) // 10**18)
    )

    # NNAG2 = A * gamma**2
    NNAG2: int = A * gamma**2 // A_MULTIPLIER

    # denominator = (GK0 + NNAG2 * x / D * K0 / 10**36)
    denominator: int = GK0 + NNAG2 * xp[0] // D * K0 // 10**36

    # p_xy = x * (GK0 + NNAG2 * y / D * K0 / 10**36) / y * 10**18 / denominator
    # p_xz = x * (GK0 + NNAG2 * z / D * K0 / 10**36) / z * 10**18 / denominator
    # p is in 10**18 precision.
    return [
        (
            xp[0]
            * (GK0 + NNAG2 * xp[1] // D * K0 // 10**36)
            // xp[1]
            * 10**18
            // denominator
        ),
        (
            xp[0]
            * (GK0 + NNAG2 * xp[2] // D * K0 // 10**36)
            // xp[2]
            * 10**18
            // denominator
        ),
    ]


# pylint: disable=too-many-locals,too-many-branches
def newton_D(  # noqa: complexity: 13
    ANN: int,
    gamma: int,
    x_unsorted: List[int],
) -> List[int]:
    """
    Finding the `D` invariant using Newton's method.

    ANN is A * N**N from the whitepaper multiplied by the
    factor A_MULTIPLIER.
    """
    n_coins: int = len(x_unsorted)

    # Safety checks
    min_A = n_coins**n_coins * A_MULTIPLIER // 10
    max_A = n_coins**n_coins * A_MULTIPLIER * 100000
    if not min_A <= ANN <= max_A:
        raise CurvesimValueError("Unsafe value for A")
    if not MIN_GAMMA <= gamma <= MAX_GAMMA:
        raise CurvesimValueError("Unsafe value for gamma")

    x: List[int] = sorted(x_unsorted, reverse=True)

    assert 10**9 <= x[0] <= 10**15 * 10**18
    for i in range(1, n_coins):
        frac: int = x[i] * 10**18 // x[0]
        assert frac >= 10**11

    D: int = n_coins * geometric_mean(x, False)
    S: int = sum(x)

    D = mpz(D)
    S = mpz(S)
    for _ in range(255):
        D_prev: int = D

        if n_coins == 2:
            K0: int = (10**18 * n_coins**2) * x[0] // D * x[1] // D
        else:
            K0: int = 10**18
            for _x in x:
                K0 = K0 * _x * n_coins // D

        _g1k0: int = abs(gamma + 10**18 - K0) + 1

        # D / (A * N**N) * _g1k0**2 / gamma**2
        mul1: int = 10**18 * D // gamma * _g1k0 // gamma * _g1k0 * A_MULTIPLIER // ANN

        # 2*N*K0 / _g1k0
        mul2: int = (2 * 10**18) * n_coins * K0 // _g1k0

        neg_fprime: int = (
            (S + S * mul2 // 10**18) + mul1 * n_coins // K0 - mul2 * D // 10**18
        )

        # D -= f / fprime
        D_plus: int = D * (neg_fprime + S) // neg_fprime
        D_minus: int = D * D // neg_fprime
        if 10**18 > K0:
            D_minus += D * (mul1 // neg_fprime) // 10**18 * (10**18 - K0) // K0
        else:
            D_minus -= D * (mul1 // neg_fprime) // 10**18 * (K0 - 10**18) // K0

        if D_plus > D_minus:
            D = D_plus - D_minus
        else:
            D = (D_minus - D_plus) // 2

        diff = abs(D - D_prev)
        # Could reduce precision for gas efficiency here
        if diff * 10**14 < max(10**16, D):
            # Test that we are safe with the next newton_y
            for _x in x:
                frac: int = _x * 10**18 // D
                if frac < 10**16 or frac > 10**20:
                    raise CalculationError("Unsafe value for x[i]")
            return int(D)

    raise CalculationError("Did not converge")
