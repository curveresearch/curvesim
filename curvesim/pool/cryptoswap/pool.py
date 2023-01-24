import time
from typing import List

from curvesim.exceptions import CalculationError, CurvesimValueError

ADMIN_ACTIONS_DELAY = 3 * 86400
MIN_RAMP_TIME = 86400

MAX_ADMIN_FEE = 10 * 10**9
MIN_FEE = 5 * 10**5  # 0.5 bps
MAX_FEE = 10 * 10**9
MAX_A_CHANGE = 10
NOISE_FEE = 10**5  # 0.1 bps

MIN_GAMMA = 10**10
MAX_GAMMA = 2 * 10**16


EXP_PRECISION = 10**10

N_COINS = 2
PRECISION = 10**18  # The precision to convert to
A_MULTIPLIER = 10000

MIN_A = N_COINS**N_COINS * A_MULTIPLIER // 10
MAX_A = N_COINS**N_COINS * A_MULTIPLIER * 100000


def _get_unix_timestamp():
    """Get the timestamp in Unix time."""
    return int(time.time())


def _geometric_mean(unsorted_x: List[int], sort: bool) -> int:
    """
    (x[0] * x[1] * ...) ** (1/N)
    """
    x: List[int] = unsorted_x
    if sort and x[0] < x[1]:
        x = [unsorted_x[1], unsorted_x[0]]
    D: int = x[0]
    diff: int = 0
    for _ in range(255):
        D_prev: int = D
        # tmp: uint256 = 10**18
        # for _x in x:
        #     tmp = tmp * _x / D
        # D = D * ((N_COINS - 1) * 10**18 + tmp) / (N_COINS * 10**18)
        # line below makes it for 2 coins
        D = (D + x[0] * x[1] // D) // N_COINS
        if D > D_prev:
            diff = D - D_prev
        else:
            diff = D_prev - D
        if diff <= 1 or diff * 10**18 < D:
            return D
    raise CalculationError("Did not converge")


def _halfpow(power: int) -> int:
    """
    1e18 * 0.5 ** (power/1e18)

    Inspired by: https://github.com/balancer-labs/balancer-core/blob/master/contracts/BNum.sol#L128
    """
    intpow: int = power // 10**18
    otherpow: int = power - intpow * 10**18
    if intpow > 59:
        return 0
    result: int = 10**18 // (2**intpow)
    if otherpow == 0:
        return result

    term: int = 10**18
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
            return result * S // 10**18

    raise CalculationError("Did not converge")


def _sqrt_int(x: int) -> int:
    """
    Originating from: https://github.com/vyperlang/vyper/issues/1266
    """

    if x == 0:
        return 0

    z: int = (x + 10**18) // 2
    y: int = x

    for i in range(256):
        if z == y:
            return y
        y = z
        z = (x * 10**18 // z + z) // 2

    raise CalculationError("Did not converge")


class CurveCryptoPool:
    def __init__(
        self,
        A: int,
        gamma: int,
        D,
        n: int,
        precisions: List[int],
        tokens: int,
        mid_fee: int,
        out_fee: int,
        allowed_extra_profit: int,
        fee_gamma: int,
        adjustment_step: int,
        admin_fee: int,
        ma_half_time: int,
        initial_price: int,
    ):
        """
        Parameters
        ----------
        A : int
            Amplification coefficient; this is :math:`A n^{n-1}` in the whitepaper.
        gamma: int
        D : int or list of int
            virtual total balance or coin balances in native token units
        n: int
            number of coins
        precisions: list of int
            precision adjustments to convert native token units to 18 decimals;
            this assumes tokens have at most 18 decimals
            i.e. balance in native units * precision = balance in D units
        tokens: int
            LP token supply
        mid_fee: int
            fee with 10**10 precision
        out_fee: int
            fee with 10**10 precision
        allowed_extra_profit: int
        fee_gamma: int
        adjustment_step:
        admin_fee: int
            percentage of `fee` with 10**10 precision
        ma_half_time: int
        initial_price: int
        """
        self.A = A
        self.gamma = gamma

        self.mid_fee = mid_fee
        self.out_fee = out_fee
        self.allowed_extra_profit = allowed_extra_profit
        self.fee_gamma = fee_gamma
        self.adjustment_step = adjustment_step
        self.admin_fee = admin_fee

        self.price_scale = initial_price
        self._price_oracle = initial_price
        self.last_prices = initial_price
        self.last_prices_timestamp = _get_unix_timestamp()
        self.ma_half_time = ma_half_time

        self.xcp_profit_a = 10**18

        self.tokens = tokens

        self.n = n
        self.precisions = precisions

        if len(precisions) != n:
            raise ValueError("`len(precisions)` must equal `n`")

        if isinstance(D, list):
            self.balances = D
        else:
            self.balances = [D // n // p for p in precisions]

        self.xcp_profit = 0
        self.xcp_profit_a = 0  # Full profit at last claim of admin fees
        # Cached (fast to read) virtual price also used internally
        self.virtual_price = 0
        self.not_adjusted = False

    def _xp(self) -> List[int]:
        precisions = self.precisions
        return [
            self.balances[0] * precisions[0],
            self.balances[1] * precisions[1] * self.price_scale // PRECISION,
        ]

    def _get_xcp(self, D: int) -> int:
        x: List[int] = [
            D // N_COINS,
            D * PRECISION // (self.price_scale * N_COINS),
        ]
        return _geometric_mean(x, True)

    @staticmethod
    def _newton_D(ANN: int, gamma: int, x_unsorted: List[int]) -> List[int]:
        """
        Finding the invariant using Newton method.
        ANN is higher by the factor A_MULTIPLIER
        ANN is already A * N**N

        Currently uses 60k gas
        """
        # Safety checks
        if ANN > MAX_A or ANN < MIN_A:
            raise CurvesimValueError("Unsafe value for A")
        if gamma > MAX_GAMMA or gamma < MIN_GAMMA:
            raise CurvesimValueError("Unsafe value for gamma")

        # Initial value of invariant D is that for constant-product invariant
        x: List[int] = x_unsorted
        if x[0] < x[1]:
            x = [x_unsorted[1], x_unsorted[0]]

        assert (
            x[0] > 10**9 - 1 and x[0] < 10**15 * 10**18 + 1
        )  # dev: unsafe values x[0]
        assert x[1] * 10**18 // x[0] > 10**14 - 1  # dev: unsafe values x[i] (input)

        D: int = N_COINS * _geometric_mean(x, False)
        S: int = x[0] + x[1]

        for _ in range(255):
            D_prev: int = D

            # K0: int = 10**18
            # for _x in x:
            #     K0 = K0 * _x * N_COINS / D
            # collapsed for 2 coins
            K0: int = (10**18 * N_COINS**2) * x[0] // D * x[1] // D

            _g1k0: int = gamma + 10**18
            if _g1k0 > K0:
                _g1k0 = _g1k0 - K0 + 1
            else:
                _g1k0 = K0 - _g1k0 + 1

            # D / (A * N**N) * _g1k0**2 / gamma**2
            mul1: int = (
                10**18 * D // gamma * _g1k0 // gamma * _g1k0 * A_MULTIPLIER // ANN
            )

            # 2*N*K0 / _g1k0
            mul2: int = (2 * 10**18) * N_COINS * K0 // _g1k0

            neg_fprime: int = (
                (S + S * mul2 // 10**18) + mul1 * N_COINS // K0 - mul2 * D // 10**18
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

            diff: int = 0
            if D > D_prev:
                diff = D - D_prev
            else:
                diff = D_prev - D
            if diff * 10**14 < max(
                10**16, D
            ):  # Could reduce precision for gas efficiency here
                # Test that we are safe with the next newton_y
                for _x in x:
                    frac: int = _x * 10**18 // D
                    if frac < 10**16 or frac > 10**20:
                        raise CalculationError("Unsafe value for x[i]")
                return D

        raise CalculationError("Did not converge")

    @staticmethod
    def _newton_y(ANN: int, gamma: int, x: List[int], D: int, i: int) -> int:
        """
        Calculating x[i] given other balances x[0..N_COINS-1] and invariant D
        ANN = A * N**N
        """
        # Safety checks
        assert ANN > MIN_A - 1 and ANN < MAX_A + 1  # dev: unsafe values A
        assert (
            gamma > MIN_GAMMA - 1 and gamma < MAX_GAMMA + 1
        )  # dev: unsafe values gamma
        assert D > 10**17 - 1 and D < 10**15 * 10**18 + 1  # dev: unsafe values D

        x_j: int = x[1 - i]
        y: int = D**2 // (x_j * N_COINS**2)
        K0_i: int = (10**18 * N_COINS) * x_j // D
        # S_i = x_j

        # frac = x_j * 1e18 / D => frac = K0_i / N_COINS
        assert (K0_i > 10**16 * N_COINS - 1) and (
            K0_i < 10**20 * N_COINS + 1
        )  # dev: unsafe values x[i]

        # x_sorted: uint256[N_COINS] = x
        # x_sorted[i] = 0
        # x_sorted = self.sort(x_sorted)  # From high to low
        # x[not i] instead of x_sorted since x_soted has only 1 element

        convergence_limit: int = max(max(x_j // 10**14, D // 10**14), 100)

        for j in range(255):
            y_prev: int = y

            K0: int = K0_i * y * N_COINS // D
            S: int = x_j + y

            _g1k0: int = gamma + 10**18
            if _g1k0 > K0:
                _g1k0 = _g1k0 - K0 + 1
            else:
                _g1k0 = K0 - _g1k0 + 1

            # D / (A * N**N) * _g1k0**2 / gamma**2
            mul1: int = (
                10**18 * D // gamma * _g1k0 // gamma * _g1k0 * A_MULTIPLIER // ANN
            )

            # 2*K0 / _g1k0
            mul2: int = 10**18 + (2 * 10**18) * K0 // _g1k0

            yfprime: int = 10**18 * y + S * mul2 + mul1
            _dyfprime: int = D * mul2
            if yfprime < _dyfprime:
                y = y_prev // 2
                continue
            else:
                yfprime -= _dyfprime
            fprime: int = yfprime // y

            # y -= f / f_prime;  y = (y * fprime - f) / fprime
            # y = (yfprime + 10**18 * D - 10**18 * S) // fprime + mul1 // fprime * (10**18 - K0) // K0
            y_minus: int = mul1 // fprime
            y_plus: int = (yfprime + 10**18 * D) // fprime + y_minus * 10**18 // K0
            y_minus += 10**18 * S // fprime

            if y_plus < y_minus:
                y = y_prev // 2
            else:
                y = y_plus - y_minus

            diff: int = 0
            if y > y_prev:
                diff = y - y_prev
            else:
                diff = y_prev - y
            if diff < max(convergence_limit, y // 10**14):
                frac: int = y * 10**18 // D
                assert (frac > 10**16 - 1) and (
                    frac < 10**20 + 1
                )  # dev: unsafe value for y
                return y

        raise CalculationError("Did not converge")

    def _tweak_price(self, A: int, gamma: int, _xp: List[int], p_i: int, new_D: int):
        price_oracle: int = self._price_oracle
        last_prices: int = self.last_prices
        price_scale: int = self.price_scale
        last_prices_timestamp: int = self.last_prices_timestamp
        p_new: int = 0

        if last_prices_timestamp < block.timestamp:
            # MA update required
            ma_half_time: int = self.ma_half_time
            alpha: int = self.halfpow(
                (block.timestamp - last_prices_timestamp) * 10**18 / ma_half_time
            )
            price_oracle = (
                last_prices * (10**18 - alpha) + price_oracle * alpha
            ) / 10**18
            self._price_oracle = price_oracle
            self.last_prices_timestamp = block.timestamp

        D_unadjusted: int = new_D  # Withdrawal methods know new D already
        if new_D == 0:
            # We will need this a few times (35k gas)
            D_unadjusted = self._newton_D(A, gamma, _xp)

        if p_i > 0:
            last_prices = p_i

        else:
            # calculate real prices
            __xp: List[int] = _xp
            dx_price: int = __xp[0] / 10**6
            __xp[0] += dx_price
            last_prices = (
                price_scale
                * dx_price
                / (_xp[1] - self._newton_y(A, gamma, __xp, D_unadjusted, 1))
            )

        self.last_prices = last_prices

        total_supply: int = self.tokens
        old_xcp_profit: int = self.xcp_profit
        old_virtual_price: int = self.virtual_price

        # Update profit numbers without price adjustment first
        xp: List[int] = [
            D_unadjusted / N_COINS,
            D_unadjusted * PRECISION / (N_COINS * price_scale),
        ]
        xcp_profit: int = 10**18
        virtual_price: int = 10**18

        if old_virtual_price > 0:
            xcp: int = _geometric_mean(xp, True)
            virtual_price = 10**18 * xcp / total_supply
            xcp_profit = old_xcp_profit * virtual_price / old_virtual_price

            t: int = self.future_A_gamma_time
            if virtual_price < old_virtual_price and t == 0:
                raise "Loss"
            if t == 1:
                self.future_A_gamma_time = 0

        self.xcp_profit = xcp_profit

        norm: int = price_oracle * 10**18 / price_scale
        if norm > 10**18:
            norm -= 10**18
        else:
            norm = 10**18 - norm
        adjustment_step: int = max(self.adjustment_step, norm / 5)

        needs_adjustment: bool = self.not_adjusted
        # if not needs_adjustment and (virtual_price-10**18 > (xcp_profit-10**18)/2 + self.allowed_extra_profit):
        # (re-arrange for gas efficiency)
        if (
            not needs_adjustment
            and (
                virtual_price * 2 - 10**18
                > xcp_profit + 2 * self.allowed_extra_profit
            )
            and (norm > adjustment_step)
            and (old_virtual_price > 0)
        ):
            needs_adjustment = True
            self.not_adjusted = True

        if needs_adjustment:
            if norm > adjustment_step and old_virtual_price > 0:
                p_new = (
                    price_scale * (norm - adjustment_step)
                    + adjustment_step * price_oracle
                ) / norm

                # Calculate balances*prices
                xp = [_xp[0], _xp[1] * p_new / price_scale]

                # Calculate "extended constant product" invariant xCP and virtual price
                D: int = self._newton_D(A, gamma, xp)
                xp = [D / N_COINS, D * PRECISION / (N_COINS * p_new)]
                # We reuse old_virtual_price here but it's not old anymore
                old_virtual_price = (
                    10**18 * self.geometric_mean(xp, True) / total_supply
                )

                # Proceed if we've got enough profit
                # if (old_virtual_price > 10**18) and (2 * (old_virtual_price - 10**18) > xcp_profit - 10**18):
                if (old_virtual_price > 10**18) and (
                    2 * old_virtual_price - 10**18 > xcp_profit
                ):
                    self.price_scale = p_new
                    self.D = D
                    self.virtual_price = old_virtual_price

                    return

                else:
                    self.not_adjusted = False

                    # Can instead do another flag variable if we want to save bytespace
                    self.D = D_unadjusted
                    self.virtual_price = virtual_price
                    self._claim_admin_fees()

                    return

        # If we are here, the price_scale adjustment did not happen
        # Still need to update the profit counter and D
        self.D = D_unadjusted
        self.virtual_price = virtual_price

        # norm appeared < adjustment_step after
        if needs_adjustment:
            self.not_adjusted = False
            self._claim_admin_fees()
