from typing import List

from gmpy2 import mpz

from curvesim.exceptions import CalculationError, CurvesimValueError
from curvesim.logging import get_logger

logger = get_logger(__name__)


MIN_GAMMA = 10**10
MAX_GAMMA = 2 * 10**16


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
        D = (D + x[0] * x[1] // D) // n_coins
        diff = abs(D_prev - D)
        if diff <= 1 or diff * 10**18 < D:
            return int(D)
    raise CalculationError("Did not converge")


def _sqrt_int(x: int) -> int:
    """
    Originating from: https://github.com/vyperlang/vyper/issues/1266
    """
    if x == 0:
        return 0

    x = mpz(x)
    z: int = (x + 10**18) // 2
    y: int = x

    for _ in range(256):
        if z == y:
            return int(y)
        y = z
        z = (x * 10**18 // z + z) // 2

    raise CalculationError("Did not converge")


def lp_price(virtual_price, price_oracle) -> int:
    """
    Returns an LP token price approximating behavior as a constant-product AMM.
    """
    price_oracle = price_oracle[0]
    return 2 * virtual_price * _sqrt_int(price_oracle) // 10**18


def newton_y(  # noqa: complexity: 11
    ANN: int,
    gamma: int,
    x: List[int],
    D: int,
    i: int,
) -> int:
    """
    Calculating x[i] given other balances x[0..n_coins-1] and invariant D
    ANN = A * N**N
    """
    n_coins: int = len(x)

    # Safety checks
    MIN_A = n_coins**n_coins * A_MULTIPLIER // 10
    MAX_A = n_coins**n_coins * A_MULTIPLIER * 100000
    if not MIN_A <= ANN <= MAX_A:
        raise CurvesimValueError("Unsafe value for A")
    if not MIN_GAMMA <= gamma <= MAX_GAMMA:
        raise CurvesimValueError("Unsafe value for gamma")
    assert 10**17 <= D <= 10**15 * 10**18
    for k in range(n_coins):
        if k != i:
            frac: int = x[k] * 10**18 // D
            assert 10**16 <= frac <= 10**20

    y: int = D // n_coins
    K0_i: int = 10**18
    S_i: int = 0

    x_sorted: List[int] = x.copy()
    x_sorted[i] = 0
    x_sorted = sorted(x_sorted, reverse=True)  # From high to low

    convergence_limit: int = max(max(x_sorted[0] // 10**14, D // 10**14), 100)
    if n_coins == 2:
        S_i: int = x[1 - i]
        y: int = D**2 // (S_i * n_coins**2)
        K0_i: int = (10**18 * n_coins) * S_i // D
    else:
        for j in range(2, n_coins + 1):
            _x: int = x_sorted[n_coins - j]
            y = y * D // (_x * n_coins)  # Small _x first
            S_i += _x
        for j in range(n_coins - 1):
            K0_i = K0_i * x_sorted[j] * n_coins // D  # Large _x first

    y = mpz(y)
    K0_i = mpz(K0_i)
    D = mpz(D)
    for _ in range(255):
        y_prev: int = y

        K0: int = K0_i * y * n_coins // D
        S: int = S_i + y

        _g1k0: int = abs(gamma + 10**18 - K0) + 1

        # D / (A * N**N) * _g1k0**2 / gamma**2
        mul1: int = 10**18 * D // gamma * _g1k0 // gamma * _g1k0 * A_MULTIPLIER // ANN

        # 2*K0 / _g1k0
        mul2: int = 10**18 + (2 * 10**18) * K0 // _g1k0

        yfprime: int = 10**18 * y + S * mul2 + mul1
        _dyfprime: int = D * mul2
        if yfprime < _dyfprime:
            y = y_prev // 2
            continue

        yfprime -= _dyfprime
        fprime: int = yfprime // y

        # y -= f / f_prime;  y = (y * fprime - f) / fprime
        # y = (yfprime + 10**18 * D - 10**18 * S)
        #   / fprime + mul1 / fprime * (10**18 - K0) / K0
        y_minus: int = mul1 // fprime
        y_plus: int = (yfprime + 10**18 * D) // fprime + y_minus * 10**18 // K0
        y_minus += 10**18 * S // fprime

        if y_plus < y_minus:
            y = y_prev // 2
        else:
            y = y_plus - y_minus

        diff: int = abs(y - y_prev)
        if diff < max(convergence_limit, y // 10**14):
            frac: int = y * 10**18 // D
            assert 10**16 <= frac <= 10**20  # dev: unsafe value for y
            return int(y)

    raise CalculationError("Did not converge")


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
