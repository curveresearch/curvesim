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

MIN_A = N_COINS**N_COINS * A_MULTIPLIER / 10
MAX_A = N_COINS**N_COINS * A_MULTIPLIER * 100000


def get_unix_timestamp():
    """Get the timestamp in Unix time."""
    return int(time.time())


class CurveCryptoPool:
    def __init__(
        self,
        A: int,
        gamma: int,
        mid_fee: int,
        out_fee: int,
        allowed_extra_profit: int,
        fee_gamma: int,
        adjustment_step: int,
        admin_fee: int,
        ma_half_time: int,
        initial_price: int,
        token,
        coins,
        precisions,
    ):
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
        self.last_prices_timestamp = get_unix_timestamp()
        self.ma_half_time = ma_half_time

        self.xcp_profit_a = 10**18

        self.token = token
        self.coins = coins
        self.PRECISIONS = precisions

        if len(coins) != len(precisions):
            raise ValueError("`coins` must have same length as `precisions`")

        self.n = len(coins)

        self.balances = [0] * self.n
        self.D = 0

        self.xcp_profit = 0
        self.xcp_profit_a = 0  # Full profit at last claim of admin fees
        # Cached (fast to read) virtual price also used internally
        self.virtual_price = 0
        self.not_adjusted = False

    def _xp(self) -> List[int]:
        precisions = self.PRECISIONS
        return [
            self.balances[0] * precisions[0],
            self.balances[1] * precisions[1] * self.price_scale / PRECISION,
        ]

    def _geometric_mean(self, unsorted_x: List[int], sort: bool) -> int:
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
            D = (D + x[0] * x[1] / D) / N_COINS
            if D > D_prev:
                diff = D - D_prev
            else:
                diff = D_prev - D
            if diff <= 1 or diff * 10**18 < D:
                return D
        raise CalculationError("Did not converge")

    def _newton_D(self, ANN: int, gamma: int, x_unsorted: List[int]) -> List[int]:
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
        assert x[1] * 10**18 / x[0] > 10**14 - 1  # dev: unsafe values x[i] (input)

        D: int = N_COINS * self._geometric_mean(x, False)
        S: int = x[0] + x[1]

        for _ in range(255):
            D_prev: int = D

            # K0: int = 10**18
            # for _x in x:
            #     K0 = K0 * _x * N_COINS / D
            # collapsed for 2 coins
            K0: int = (10**18 * N_COINS**2) * x[0] / D * x[1] / D

            _g1k0: int = gamma + 10**18
            if _g1k0 > K0:
                _g1k0 = _g1k0 - K0 + 1
            else:
                _g1k0 = K0 - _g1k0 + 1

            # D / (A * N**N) * _g1k0**2 / gamma**2
            mul1: int = (
                10**18 * D / gamma * _g1k0 / gamma * _g1k0 * A_MULTIPLIER / ANN
            )

            # 2*N*K0 / _g1k0
            mul2: int = (2 * 10**18) * N_COINS * K0 / _g1k0

            neg_fprime: int = (
                (S + S * mul2 / 10**18) + mul1 * N_COINS / K0 - mul2 * D / 10**18
            )

            # D -= f / fprime
            D_plus: int = D * (neg_fprime + S) / neg_fprime
            D_minus: int = D * D / neg_fprime
            if 10**18 > K0:
                D_minus += D * (mul1 / neg_fprime) / 10**18 * (10**18 - K0) / K0
            else:
                D_minus -= D * (mul1 / neg_fprime) / 10**18 * (K0 - 10**18) / K0

            if D_plus > D_minus:
                D = D_plus - D_minus
            else:
                D = (D_minus - D_plus) / 2

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
                    frac: int = _x * 10**18 / D
                    if frac < 10**16 or frac > 10**20:
                        raise CalculationError("Unsafe value for x[i]")
                return D

        raise CalculationError("Did not converge")
