"""
Auxiliary calculations needed for the tricrypto implementation.

This is loosely the python counterpart to the Tricrypto math contract.
"""
from math import isqrt
from typing import List

from gmpy2 import mpz

from curvesim.exceptions import CalculationError, CurvesimValueError
from curvesim.logging import get_logger

logger = get_logger(__name__)

NOISE_FEE = 10**5  # 0.1 bps

MIN_GAMMA = 10**10
MAX_GAMMA = 5 * 10**16

EXP_PRECISION = 10**10

PRECISION = 10**18  # The precision to convert to
A_MULTIPLIER = 10000

N_COINS = 3
MIN_A: int = N_COINS**N_COINS * A_MULTIPLIER // 100
MAX_A: int = N_COINS**N_COINS * A_MULTIPLIER * 1000


# pylint: disable-next=too-many-locals,too-many-statements,too-many-branches
def get_y(  # noqa: complexity: 18
    ANN: int,
    gamma: int,
    x: List[int],
    D: int,
    i: int,
) -> List[int]:
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
    assert MIN_A <= ANN <= MAX_A
    assert MIN_GAMMA <= gamma <= MAX_GAMMA
    assert 10**17 <= D <= 10**15 * 10**18

    frac: int = 0
    for _k in range(3):
        if _k != i:
            frac = x[_k] * 10**18 // D
            assert 10**16 <= frac <= 10**20, "Unsafe values x[i]"
            # if above conditions are met, x[_k] > 0

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

    x_j: int = mpz(x[j])
    x_k: int = mpz(x[k])
    gamma = mpz(gamma)
    gamma2: int = gamma**2

    a: int = 10**36 // 27

    # 10**36/9 + 2*10**18*gamma/27
    #   - D**2/x_j*gamma**2*ANN/27**2/convert(A_MULTIPLIER, int256)/x_k
    b: int = (
        10**36 // 9
        + 2 * 10**18 * gamma // 27
        - D**2 // x_j * gamma2 * ANN // 27**2 // A_MULTIPLIER // x_k
    )

    # Vyper does signed integer division, rounding towards zero, so we need
    # to track the sign of b, to flip signs before and after python integer
    # division.
    b_is_neg = b < 0

    # 10**36/9 + gamma*(gamma + 4*10**18)/27
    #   + gamma**2*(x_j+x_k-D)/D*ANN/27/convert(A_MULTIPLIER, int256)
    c: int = 10**36 // 9 + gamma * (gamma + 4 * 10**18) // 27
    _c_neg: int = x_j + x_k - D
    if _c_neg < 0:
        # since vyper will do signed integer division, which rounds toward 0,
        # we switch signs to round appropriately and then change the sign back
        _c: int = gamma2 * (-1 * _c_neg) // D * ANN // 27 // A_MULTIPLIER
        _c *= -1
    else:
        _c = gamma2 * _c_neg // D * ANN // 27 // A_MULTIPLIER
    c += _c
    c_is_neg = c < 0

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
    if b_is_neg:
        b *= -1
    if c_is_neg:
        c *= -1
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
    if b_is_neg:
        b *= -1
    if c_is_neg:
        c *= -1

    # 3*a*c/b - b
    _3ac: int = (3 * a) * c
    if sign(_3ac) != sign(b):
        delta0: int = -(_3ac // -b) - b
    else:
        delta0 = _3ac // b - b

    # 9*a*c/b - 2*b - 27*a**2/b*d/b
    if sign(_3ac) != sign(b):
        delta1: int = -(3 * _3ac // -b) - 2 * b
    else:
        delta1 = 3 * _3ac // b - 2 * b
    if b_is_neg:
        delta1 -= 27 * a**2 // -b * d // -b
    else:
        delta1 -= 27 * a**2 // b * d // b

    # delta1**2 + 4*delta0**2/b*delta0
    if b_is_neg:
        sqrt_arg: int = delta1**2 - (4 * delta0**2 // -b * delta0)
    else:
        sqrt_arg = delta1**2 + 4 * delta0**2 // b * delta0

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
        second_cbrt = _cbrt((delta1 + sqrt_val) // 2)
    else:
        second_cbrt = -_cbrt(-(delta1 - sqrt_val) // 2)

    # b_cbrt*b_cbrt/10**18*second_cbrt/10**18
    if second_cbrt < 0:
        C1: int = -(b_cbrt * b_cbrt // 10**18 * -second_cbrt // 10**18)
    else:
        C1 = b_cbrt * b_cbrt // 10**18 * second_cbrt // 10**18

    # (b + b*delta0/C1 - C1)/3
    if sign(b * delta0) != sign(C1):
        root_K0: int = (b + -(b * delta0 // -C1) - C1) // 3
    else:
        root_K0 = (b + b * delta0 // C1 - C1) // 3

    # D*D/27/x_k*D/x_j*root_K0/a
    root: int = D * D // 27 // x_k * D // x_j * root_K0 // a

    out: List[int] = [int(root), int(10**18 * root_K0 // a)]

    frac = out[0] * 10**18 // D
    assert 10**16 <= frac <= 10**20, "Unsafe value for y"
    # due to precision issues, get_y can be off by 2 wei or so wrt _newton_y

    return out


def sign(x):
    """Return +/-1 depending on sign of number.  0 is positive."""
    return -1 if x < 0 else 1


def _newton_y(  # noqa: complexity: 11  # pylint: disable=duplicate-code,too-many-locals
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
            frac = y * 10**18 // D
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


def lp_price(virtual_price: int, price_oracle: List[int]) -> int:
    """
    Returns the price of an LP token in units of token 0.

    Derived from the equilibrium point of a constant-product AMM
    that approximates Cryptoswap's behavior.

    Parameters
    ----------
    virtual_price: int
        Amount of XCP invariant per LP token in units of `D`.
    price_oracle: List[int]
        Price oracle value for the pool.

    Returns
    -------
    int
        Liquidity redeemable per LP token in units of token 0.
    """
    p_0: int = price_oracle[0]
    p_1: int = price_oracle[1]

    return 3 * virtual_price * _cbrt(p_0 * p_1) // 10**24


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


def newton_D(  # pylint: disable=too-many-locals
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
    assert x[0] < (2**256 - 1) // 10**18 * N_COINS**N_COINS
    assert x[0] > 0

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

    D = mpz(D)

    for _ in range(255):
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
        _g1k0 = abs(_g1k0 - K0) + 1

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

        # neg_fprime: int = (S + S * mul2 / 10**18)
        #                   + mul1 * N_COINS / K0 - mul2 * D / 10**18
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

        diff: int = abs(D - D_prev)
        # Could reduce precision for gas efficiency here:
        if diff * 10**14 < max(10**16, D):
            # Test that we are safe with the next get_y
            for _x in x:
                frac: int = (_x * 10**18) // D
                assert 10**16 <= frac <= 10**20, "Unsafe values x[i]"
            return int(D)

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


def wad_exp(x: int) -> int:
    """
    @notice Calculates the e**x with 1e18 precision
    @param x The 32-byte variable to calculate the exponential of.
    @return int256 The 32-byte calculation result.

    @dev Calculates the natural exponential function of a signed integer with
         a precision of 1e18.
    @notice Note that this function consumes about 810 gas units. The implementation
            is inspired by Remco Bloemen's implementation under the MIT license here:
            https://xn--2-umb.com/22/exp-ln.
    @dev This implementation is derived from Snekmate, which is authored
         by pcaversaccio (Snekmate), distributed under the AGPL-3.0 license.
         https://github.com/pcaversaccio/snekmate
    """
    value: int = x

    # If the result is `< 0.5`, we return zero. This happens when we have the following:
    # "x <= floor(log(0.5e18) * 1e18) ~ -42e18".
    if x <= -42139678854452767551:
        return 0

    # When the result is "> (2 ** 255 - 1) / 1e18" we cannot represent it
    # as a signed integer.
    # This happens when "x >= floor(log((2 ** 255 - 1) / 1e18) * 1e18) ~ 135".
    assert x < 135305999368893231589, "wad_exp overflow"

    # `x` is now in the range "(-42, 136) * 1e18".
    # Convert to "(-42, 136) * 2 ** 96" for higher intermediate precision
    # and a binary base. This base conversion is a multiplication with
    # "1e18 / 2 ** 96 = 5 ** 18 / 2 ** 78".
    value = (x << 78) // 5**18

    # Reduce the range of `x` to "(-½ ln 2, ½ ln 2) * 2 ** 96" by
    # factoring out powers of two so that "exp(x) = exp(x') * 2 ** k",
    # where `k` is a signer integer. Solving this gives
    # "k = round(x / log(2))" and "x' = x - k * log(2)".
    # Thus, `k` is in the range "[-61, 195]".
    k: int = ((value << 96) // 54916777467707473351141471128 + 2**95) >> 96
    value = value - (k * 54916777467707473351141471128)

    # Evaluate using a "(6, 7)"-term rational approximation. Since `p` is monic,
    # we will multiply by a scaling factor later.
    y: int = (
        ((value + 1346386616545796478920950773328) * value) >> 96
    ) + 57155421227552351082224309758442
    p: int = (
        ((((y + value) - 94201549194550492254356042504812) * y) >> 96)
        + 28719021644029726153956944680412240
    ) * value + (4385272521454847904659076985693276 << 96)

    # We leave `p` in the "2 ** 192" base so that we do not have to scale it up
    # again for the division.
    q: int = (
        ((value - 2855989394907223263936484059900) * value) >> 96
    ) + 50020603652535783019961831881945
    q = ((q * value) >> 96) - 533845033583426703283633433725380
    q = ((q * value) >> 96) + 3604857256930695427073651918091429
    q = ((q * value) >> 96) - 14423608567350463180887372962807573
    q = ((q * value) >> 96) + 26449188498355588339934803723976023

    # The polynomial `q` has no zeros in the range because all its roots are complex.
    # No scaling is required, as `p` is already "2 ** 96" too large. Also,
    # `r` is in the range "(0.09, 0.25) * 2**96" after the division.
    r: int = p // q

    # To finalise the calculation, we have to multiply `r` by:
    #   - the scale factor "s = ~6.031367120",
    #   - the factor "2 ** k" from the range reduction, and
    #   - the factor "1e18 / 2 ** 96" for the base conversion.
    # We do this all at once, with an intermediate result in "2**213" base,
    # so that the final right shift always gives a positive value.

    # Note that to circumvent Vyper's safecast feature for the potentially
    # negative parameter value `r`, we first convert `r` to `bytes32` and
    # subsequently to `uint256`. Remember that the EVM default behaviour is
    # to use two's complement representation to handle signed integers.
    return (r * 3822833074963236453042738258902158003155416615667) >> (195 - k)
