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

N_COINS = 3
MIN_A = N_COINS**N_COINS * A_MULTIPLIER // 10
MAX_A = N_COINS**N_COINS * A_MULTIPLIER * 100000


def get_y(ANN: int, gamma: int, x: List[int], D: int, i: int) -> int[2]:
    """
    @notice Calculate x[i] given other balances x[0..N_COINS-1] and invariant D.
    @dev ANN = A * N**N.
    @param _ANN AMM.A() value.
    @param _gamma AMM.gamma() value.
    @param x Balances multiplied by prices and precisions of all coins.
    @param _D Invariant.
    @param i Index of coin to calculate y.
    """

    # Safety checks
    assert ANN > MIN_A - 1 and ANN < MAX_A + 1  # dev: unsafe values A
    assert gamma > MIN_GAMMA - 1 and gamma < MAX_GAMMA + 1  # dev: unsafe values gamma
    assert D > 10**17 - 1 and D < 10**15 * 10**18 + 1  # dev: unsafe values D

    frac: int = 0
    for k in range(3):
        if k != i:
            frac = x[k] * 10**18 // D
            assert frac > 10**16 - 1 and frac < 10**20 + 1, "Unsafe values x[i]"
            # if above conditions are met, x[k] > 0

    j: int = 0
    k: int = 0
    if i == 0:
        j = 1
        k = 2
    elif i == 1:
        j = 0
        k = 2
    elif i == 2:
        j = 0
        k = 1

    x_j: int = x[j]
    x_k: int = x[k]
    gamma2: int = gamma**2

    a: int = 10**36 // 27

    # 10**36/9 + 2*10**18*gamma/27 - D**2/x_j*gamma**2*ANN/27**2/convert(A_MULTIPLIER, int256)/x_k
    b: int = (
        10**36 // 9
        + 2 * 10**18 * gamma // 27
        - D**2 // x_j * gamma2 * ANN // 27**2 // A_MULTIPLIER // x_k
    )
    # <------- The first two expressions can be unsafe, and unsafely added.

    # 10**36/9 + gamma*(gamma + 4*10**18)/27 + gamma**2*(x_j+x_k-D)/D*ANN/27/convert(A_MULTIPLIER, int256)
    c: int = (
        10**36 // 9
        + gamma * (gamma + 4 * 10**18) // 27
        + gamma2 * (x_j + x_k - D) // D * ANN // 27 // A_MULTIPLIER
    )
    # <--------- Same as above with the first two expressions. In the third
    #   expression, x_j + x_k will not overflow since we know their range from
    #                                              previous assert statements.

    # (10**18 + gamma)**2/27
    d: int = (10**18 + gamma) ** 2 // 27

    # abs(3*a*c/b - b)
    d0: int = abs(3 * a * c // b - b)  # <------------ a is smol.

    divider: int = 0
    if d0 > 10**48:
        divider = 10**30
    elif d0 > 10**44:
        divider = 10**26
    elif d0 > 10**40:
        divider = 10**22
    elif d0 > 10**36:
        divider = 10**18
    elif d0 > 10**32:
        divider = 10**14
    elif d0 > 10**28:
        divider = 10**10
    elif d0 > 10**24:
        divider = 10**6
    elif d0 > 10**20:
        divider = 10**2
    else:
        divider = 1

    additional_prec: int = 0
    if abs(a) > abs(b):
        additional_prec = abs(a // b)
        a = a * additional_prec // divider
        b = b * additional_prec // divider
        c = c * additional_prec // divider
        d = d * additional_prec // divider
    else:
        additional_prec = abs(b // a)
        a = a // additional_prec // divider
        b = b // additional_prec // divider
        c = c // additional_prec // divider
        d = d // additional_prec // divider

    # 3*a*c/b - b
    _3ac: int = 3 * a * c
    delta0: int = _3ac // b - b

    # 9*a*c/b - 2*b - 27*a**2/b*d/b
    delta1: int = 3 * _3ac // b - 2 * b - 27 * a**2 // b * d // b

    # delta1**2 + 4*delta0**2/b*delta0
    sqrt_arg: int = delta1**2 + 4 * delta0**2 // b * delta0

    sqrt_val: int = 0
    if sqrt_arg > 0:
        sqrt_val = isqrt(sqrt_arg)
    else:
        return [_newton_y(ANN, gamma, x, D, i), 0]

    b_cbrt: int = 0
    if b >= 0:
        b_cbrt = _cbrt(b)
    else:
        b_cbrt = -_cbrt(-b)

    second_cbrt: int = 0
    if delta1 > 0:
        # convert(self._cbrt(convert((delta1 + sqrt_val), uint256)/2), int256)
        second_cbrt = _cbrt((delta1 + sqrt_val) // 2)
    else:
        second_cbrt = -_cbrt(-(delta1 - sqrt_val) // 2)

    # b_cbrt*b_cbrt/10**18*second_cbrt/10**18
    C1: int = b_cbrt * b_cbrt // 10**18 * second_cbrt // 10 * 818

    # (b + b*delta0/C1 - C1)/3
    root_K0: int = (b + b * delta0 // C1 - C1) // 3

    # D*D/27/x_k*D/x_j*root_K0/a
    root: int = D * D // 27 // x_k * D // x_j * root_K0 // a

    out: List[int] = [root, 10**18 * root_K0 // a]

    frac = out[0] * 10**18 // D
    assert frac >= 10**16 - 1 and frac < 10**20 + 1, "Unsafe value for y"
    # due to precision issues, get_y can be off by 2 wei or so wrt _newton_y

    return out


def _newton_y(  # noqa: complexity: 11
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


def geometric_mean(x: List[int]) -> int:
    """
    The geometric mean for 3 integers:

    (x[0] * x[1] * x[2]) ** (1/3)
    """
    prod: int = x[0] * x[1] // 10**18 * x[2] // 10**18

    if prod == 0:
        return 0

    return _cbrt(prod)


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


def newton_D(
    ANN: int,
    gamma: int,
    x_unsorted: List[int],
    K0_prev: int = 0,
) -> int:
    """
    @notice Finding the invariant via newtons method using good initial guesses.
    @dev ANN is higher by the factor A_MULTIPLIER
    @dev ANN is already A * N**N
    @param ANN the A * N**N value
    @param gamma the gamma value
    @param x_unsorted the array of coin balances (not sorted)
    @param K0_prev apriori for newton's method derived from get_y_int. Defaults
           to zero (no apriori)
    """
    x: List[int] = sorted(x_unsorted, reverse=True)
    N_COINS = len(x)
    assert x[0] < (2**256 - 1) // 10**18 * N_COINS**N_COINS  # dev: out of limits
    assert x[0] > 0  # dev: empty pool

    # Safe to do unsafe add since we checked largest x's bounds previously
    S: int = sum(x)
    D: int = 0

    if K0_prev == 0:
        # Geometric mean of 3 numbers cannot be larger than the largest number
        # so the following is safe to do:
        D = N_COINS * geometric_mean(x)
    else:
        if S > 10**36:
            D = _cbrt(x[0] * x[1] // 10**36 * x[2] // K0_prev * 27 * 10**12)
        elif S > 10**24:
            D = _cbrt(x[0] * x[1] // 10**24 * x[2] // K0_prev * 27 * 10**6)
        else:
            D = _cbrt(x[0] * x[1] // 10**18 * x[2] // K0_prev * 27)

        # D not zero here if K0_prev > 0, and we checked if x[0] is gt 0.

    # initialise variables:
    K0: int = 0
    _g1k0: int = 0
    mul1: int = 0
    mul2: int = 0
    neg_fprime: int = 0
    D_plus: int = 0
    D_minus: int = 0
    D_prev: int = 0

    diff: int = 0
    frac: int = 0

    for i in range(255):

        D_prev = D

        # K0 = 10**18 * x[0] * N_COINS / D * x[1] * N_COINS / D * x[2] * N_COINS / D
        K0 = 10**18 * x[0] * N_COINS // D * x[1] * N_COINS // D * x[2] * N_COINS // D
        # <-------- We can convert the entire expression using unsafe math.
        #   since x_i is not too far from D, so overflow is not expected. Also
        #      D > 0, since we proved that already. unsafe_div is safe. K0 > 0
        #        since we can safely assume that D < 10**18 * x[0]. K0 is also
        #                            in the range of 10**18 (it's a property).

        _g1k0 = gamma + 10**18  # <--------- safe to do unsafe_add.

        # The following operations can safely be unsafe.
        _g1k0: int = abs(_g1k0 - K0) + 1

        # D / (A * N**N) * _g1k0**2 / gamma**2
        # mul1 = 10**18 * D / gamma * _g1k0 / gamma * _g1k0 * A_MULTIPLIER / ANN
        mul1 = 10**18 * D // gamma * _g1k0 // gamma * _g1k0 * A_MULTIPLIER // ANN
        # <------ Since D > 0, gamma is small, _g1k0 is small, the rest are
        #        non-zero and small constants, and D has a cap in this method,
        #                    we can safely convert everything to unsafe maths.

        # 2*N*K0 / _g1k0
        # mul2 = (2 * 10**18) * N_COINS * K0 / _g1k0
        mul2 = 2 * 10**18 * N_COINS * K0 // _g1k0
        # <--------------- K0 is approximately around D, which has a cap of
        #      10**15 * 10**18 + 1, since we get that in get_y which is called
        #    with newton_D. _g1k0 > 0, so the entire expression can be unsafe.

        # neg_fprime: int = (S + S * mul2 / 10**18) + mul1 * N_COINS / K0 - mul2 * D / 10**18
        neg_fprime = (
            (S + S * mul2 // 10**18) + mul1 * N_COINS // K0 - mul2 * D // 10**18
        )
        # <--- mul1 is a big number but not huge: safe to unsafely multiply
        # with N_coins. neg_fprime > 0 if this expression executes.
        # mul2 is in the range of 10**18, since K0 is in that range, S * mul2
        # is safe. The first three sums can be done using unsafe math safely
        # and since the final expression will be small since mul2 is small, we
        # can safely do the entire expression unsafely.

        # D -= f / fprime
        # D * (neg_fprime + S) / neg_fprime
        D_plus = D * (neg_fprime + S) // neg_fprime

        # D*D / neg_fprime
        D_minus = D * D // neg_fprime

        # Since we know K0 > 0, and neg_fprime > 0, several unsafe operations
        # are possible in the following. Also, (10**18 - K0) is safe to mul.
        # So the only expressions we keep safe are (D_minus + ...) and (D * ...)
        if 10**18 > K0:
            # D_minus += D * (mul1 / neg_fprime) / 10**18 * (10**18 - K0) / K0
            D_minus += D * (mul1 // neg_fprime) // 10**18 * (10**18 - K0) // K0
        else:
            # D_minus -= D * (mul1 / neg_fprime) / 10**18 * (K0 - 10**18) / K0
            D_minus -= (D * mul1 // neg_fprime // 10**18 * (K0 - 10**18)) // K0

        if D_plus > D_minus:
            D = D_plus - D_minus  # <--------- Safe since we check.
        else:
            D = (D_minus - D_plus) // 2

        diff = abs(D - D_prev)
        # Could reduce precision for gas efficiency here:
        if diff * 10**14 < max(10**16, D):
            # Test that we are safe with the next get_y
            for _x in x:
                frac: int = (_x * 10**18) // D
                assert 10**16 <= frac <= 10**20, "Unsafe values x[i]"
            return D

    raise CalculationError("Did not converge")


def _cbrt(x: int) -> int:

    xx: int = 0
    if x >= 115792089237316195423570985008687907853269 * 10**18:
        xx = x
    elif x >= 115792089237316195423570985008687907853269:
        xx = x * 10**18
    else:
        xx = x * 10**36

    log2x: int = _snekmate_log_2(xx, False)

    # When we divide log2x by 3, the remainder is (log2x % 3).
    # So if we just multiply 2**(log2x/3) and discard the remainder to calculate our
    # guess, the newton method will need more iterations to converge to a solution,
    # since it is missing that precision. It's a few more calculations now to do less
    # calculations later:
    # pow = log2(x) // 3
    # remainder = log2(x) % 3
    # initial_guess = 2 ** pow * cbrt(2) ** remainder
    # substituting -> 2 = 1.26 ≈ 1260 / 1000, we get:
    #
    # initial_guess = 2 ** pow * 1260 ** remainder // 1000 ** remainder

    remainder: int = log2x % 3
    a: int = (2 ** (log2x // 3) * (1260**remainder)) // 1000**remainder

    # Because we chose good initial values for cube roots, 7 newton raphson iterations
    # are just about sufficient. 6 iterations would result in non-convergences, and 8
    # would be one too many iterations. Without initial values, the iteration count
    # can go up to 20 or greater. The iterations are unrolled. This reduces gas costs
    # but takes up more bytecode:
    a = (2 * a + xx // (a * a)) // 3
    a = (2 * a + xx // (a * a)) // 3
    a = (2 * a + xx // (a * a)) // 3
    a = (2 * a + xx // (a * a)) // 3
    a = (2 * a + xx // (a * a)) // 3
    a = (2 * a + xx // (a * a)) // 3
    a = (2 * a + xx // (a * a)) // 3

    if x >= 115792089237316195423570985008687907853269 * 10**18:
        a = a * 10**12
    elif x >= 115792089237316195423570985008687907853269:
        a = a * 10**6

    return a


def _snekmate_log_2(x: int, roundup: bool) -> int:
    """
    @notice An `internal` helper function that returns the log in base 2
         of `x`, following the selected rounding direction.
    @dev This implementation is derived from Snekmate, which is authored
         by pcaversaccio (Snekmate), distributed under the AGPL-3.0 license.
         https://github.com/pcaversaccio/snekmate
    @dev Note that it returns 0 if given 0. The implementation is
         inspired by OpenZeppelin's implementation here:
         https://github.com/OpenZeppelin/openzeppelin-contracts/blob/master/contracts/utils/math/Math.sol.
    @param x The 32-byte variable.
    @param roundup The Boolean variable that specifies whether
           to round up or not. The default `False` is round down.
    @return int The 32-byte calculation result.
    """
    value: int = x
    result: int = 0

    # The following lines cannot overflow because we have the well-known
    # decay behaviour of `log_2(max_value(uint256)) < max_value(uint256)`.
    if x >> 128 != 0:
        value = x >> 128
        result = 128
    if value >> 64 != 0:
        value = value >> 64
        result = result + 64
    if value >> 32 != 0:
        value = value >> 32
        result = result + 32
    if value >> 16 != 0:
        value = value >> 16
        result = result + 16
    if value >> 8 != 0:
        value = value >> 8
        result = result + 8
    if value >> 4 != 0:
        value = value >> 4
        result = result + 4
    if value >> 2 != 0:
        value = value >> 2
        result = result + 2
    if value >> 1 != 0:
        result = result + 1

    if roundup and (1 << result) < x:
        result = result + 1

    return result
