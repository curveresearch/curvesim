"""
Mainly a module to house the `CryptoPool`, a cryptoswap implementation in Python.
"""
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


# pylint: disable-next=too-many-instance-attributes
class CurveCryptoPool(Pool):
    """Cryptoswap implementation in Python."""

    __slots__ = (
        "A",
        "gamma",
        "n",
        "precisions",
        "mid_fee",
        "out_fee",
        "allowed_extra_profit",
        "fee_gamma",
        "adjustment_step",
        "admin_fee",
        "ma_half_time",
        "price_scale",
        "_price_oracle",
        "last_prices",
        "last_prices_timestamp",
        "_block_timestamp",
        "balances",
        "D",
        "virtual_price",
        "tokens",
        "xcp_profit",
        "xcp_profit_a",
        "not_adjusted",
    )

    # pylint: disable-next=too-many-locals,too-many-arguments
    def __init__(
        self,
        A: int,
        gamma: int,
        n: int,
        precisions: List[int],
        mid_fee: int,
        out_fee: int,
        allowed_extra_profit: int,
        fee_gamma: int,
        adjustment_step: int,
        ma_half_time: int,
        price_scale: List[int],
        price_oracle=None,
        last_prices=None,
        balances=None,
        D=None,
        tokens=None,
        admin_fee: int = 5 * 10**9,
        xcp_profit=10**18,
        xcp_profit_a=10**18,
    ):
        """
        Parameters
        ----------
        A : int
            Amplification coefficient; this is :math:`A n^n` in the whitepaper
            multiplied by 10**4 for greater precision.
        gamma: int
            Decay factor for A.
        n: int
            Number of coins; currently only n = 2 is supported.
        precisions: list of int
            Precision adjustments to convert native token units to 18 decimals;
            this assumes tokens have at most 18 decimals
            i.e. balance in native units * precision = balance in D units
        mid_fee: int
            Fee with 10**10 precision, for trades near price scale
        out_fee: int
            Fee with 10**10 precision, used to adjust `mid_fee` for trades
            further away from price_scale
        allowed_extra_profit: int
            "Buffer" used to determine if the price adjustment algorithm
            should run.
        fee_gamma: int
            Factor used to control the transition from `mid_fee` to `out_fee`.
        adjustment_step:
            Minimum step size to adjust the price scale.
        ma_half_time: int
            "Half-life" for exponential moving average of trade prices.
        price_scale: List[Int]
            Price scale value for the pool.  This is where liquidity is concentrated.
        price_oracle: List[Int], optional
            Price oracle value for the pool.  This is the EMA price used to
            adjust the price scale toward.
            Defaults to `price_scale`.
        last_prices: List[Int], optional
            Last trade price for the pool.
            Defaults to `price_scale`.
        balances: list of int, optional
            Coin balances in native token units;
            either `balances` or `D` is required
        D : int, optional
            Stableswap invariant for given balances, precisions, price_scale,
            A, and gamma; either `balances` or `D` is required
        tokens: int, optional
            LP token supply (default is calculated from `D`, which is also
            calculated if needed)
        admin_fee: int, optional
            Percentage of `fee` with 10**10 precision.  Fee paid to the DAO
            (default = 5*10**9)
        xcp_profit: int, optional
            Counter for accumulated profits, no losses (default = 10**18)
        xcp_profit_a: int, optional
            Value of `xcp_profit` when admin fees last claimed (default = 10**18)
        """
        self.A = A
        self.gamma = gamma

        self.mid_fee = mid_fee
        self.out_fee = out_fee
        self.allowed_extra_profit = allowed_extra_profit
        self.fee_gamma = fee_gamma
        self.adjustment_step = adjustment_step
        self.admin_fee = admin_fee

        self.price_scale = price_scale
        self._price_oracle = price_oracle or price_scale
        self.last_prices = last_prices or price_scale
        self.ma_half_time = ma_half_time

        self._block_timestamp = _get_unix_timestamp()
        self.last_prices_timestamp = self._block_timestamp

        self.xcp_profit = xcp_profit
        self.xcp_profit_a = xcp_profit_a  # Full profit at last claim of admin fees
        self.not_adjusted = False

        if n not in [2, 3]:
            raise CryptoPoolError(
                "Only 2 or 3-coin crypto pools are currently supported."
            )
        self.n = n
        self.precisions = precisions

        if len(precisions) != n:
            raise ValueError("`len(precisions)` must equal `n`")

        if balances is None and D is None:
            raise ValueError("Must provide at least one of `balances` or `D`.")

        # All state variables needed for balance conversions or "newton"
        # calculations should have been set by this point.

        if balances:
            self.balances = balances

        if D is not None:
            self.D = D
            if not balances:
                self.balances = self._convert_D_to_balances(D)
            else:
                # If user passes both `D` and `balances`, it's possible
                # they may be inconsistent; however we allow this for
                # unanticipated use-cases.
                logger.warning(
                    "Both `D` and `balances` were passed into `__init__`. "
                    "Inconsistent values may create issues."
                )
        else:
            xp = self._xp()
            D = self._newton_D(A, gamma, xp)
            self.D = D

        xcp = self._get_xcp(D)
        if tokens is not None:
            self.tokens = tokens
        else:
            self.tokens = xcp

        self.virtual_price = 10**18 * xcp // tokens

    def _convert_D_to_balances(self, D):
        price_scale = self.price_scale
        precisions = self.precisions
        n = self.n

        return [D // n] + [
            D * PRECISION // (p * n) // prec
            for p, prec in zip(price_scale, precisions[1:])
        ]

    def _xp(self) -> List[int]:
        """
        Calculate the balances in units of `D`, converting using `price_scale`
        so a unit of each token has equal value.

        Returns
        --------
        List[int]
            The pool balances in units of `D`.

        Note
        -----
        This intentionally always return a new copy of the balances.
        """
        balances = self.balances
        return self._xp_mem(balances)

    def _xp_mem(self, balances) -> List[int]:
        """
        Parameters
        ----------
        balances: List[int]
            The pool balances in native token units.

        Returns
        --------
        List[int]
            The pool balances in units of `D`.

        Note
        -----
        This intentionally always return a new copy of the balances.
        """
        precisions = self.precisions
        price_scale = self.price_scale
        return [balances[0] * precisions[0]] + [
            balance * precision * price // PRECISION
            for balance, precision, price in zip(
                balances[1:], precisions[1:], price_scale
            )
        ]

    def _get_xcp(self, D: int) -> int:
        """
        Calculate the constant-product profit, using the balances at
        equilibrium point.
        """
        n_coins: int = self.n
        price_scale: List[int] = self.price_scale
        x = [D // n_coins] + [
            D * PRECISION // (price * n_coins) for price in price_scale
        ]
        return _geometric_mean(x, True)

    # pylint: disable=too-many-locals,too-many-branches
    @staticmethod
    def _newton_D(  # noqa: complexity: 13
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
        if ANN > max_A or ANN < min_A:
            raise CurvesimValueError("Unsafe value for A")
        if gamma > MAX_GAMMA or gamma < MIN_GAMMA:
            raise CurvesimValueError("Unsafe value for gamma")

        x: List[int] = sorted(x_unsorted, reverse=True)

        # FIXME: extend to n coins
        assert (
            x[0] > 10**9 - 1 and x[0] < 10**15 * 10**18 + 1
        )  # dev: unsafe values x[0]
        assert x[1] * 10**18 // x[0] > 10**14 - 1  # dev: unsafe values x[i] (input)

        D: int = n_coins * _geometric_mean(x, False)
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

    @staticmethod
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
        assert ANN > MIN_A - 1 and ANN < MAX_A + 1  # dev: unsafe values A
        assert (
            gamma > MIN_GAMMA - 1 and gamma < MAX_GAMMA + 1
        )  # dev: unsafe values gamma
        assert D > 10**17 - 1 and D < 10**15 * 10**18 + 1  # dev: unsafe values D
        for k in range(n_coins):
            if k != i:
                frac: int = x[k] * 10**18 // D
                assert (frac > 10**16 - 1) and (
                    frac < 10**20 + 1
                )  # dev: unsafe values x[i]

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

    def _increment_timestamp(self, blocks=1, timestamp=None):
        """Update the internal clock used to mimic the block timestamp."""
        if timestamp:
            self._block_timestamp = timestamp
            return

        self._block_timestamp += 12 * blocks

    # pylint: disable=too-many-statements
    def _tweak_price(  # noqa: complexity: 12
        self,
        A: int,
        gamma: int,
        _xp: List[int],
        i: int,
        p_i: int,
        new_D: int,
    ):
        """
        Applies several kinds of updates:
            - EMA price update: price_oracle
            - Profit counters: D, virtual_price, xcp_profit
            - price adjustment: price_scale

        Also claims admin fees if appropriate (enough profit and price scale
        and oracle is close enough).
        """
        price_oracle: List[int] = self._price_oracle
        last_prices: List[int] = self.last_prices
        price_scale: List[int] = self.price_scale
        last_prices_timestamp: int = self.last_prices_timestamp
        block_timestamp: int = self._block_timestamp
        n_coins: int = self.n

        # Update EMA price oracle for a new block.  Happens once per block.
        # EMA uses price of the last trade and oracle price in previous block.
        if last_prices_timestamp < block_timestamp:
            ma_half_time: int = self.ma_half_time
            alpha: int = _halfpow(
                (block_timestamp - last_prices_timestamp) * 10**18 // ma_half_time
            )
            price_oracle = [
                (last_p * (10**18 - alpha) + oracle_p * alpha) // 10**18
                for last_p, oracle_p in zip(last_prices, price_oracle)
            ]
            self._price_oracle = price_oracle
            self.last_prices_timestamp = block_timestamp

        D_unadjusted: int = new_D  # Withdrawal methods know new D already
        if new_D == 0:
            D_unadjusted = self._newton_D(A, gamma, _xp)

        if p_i > 0:
            # Save the last price
            if i > 0:
                last_prices[i - 1] = p_i
            else:
                # If 0th price changed - change all prices instead
                for k in range(n_coins - 1):
                    last_prices[k] = last_prices[k] * 10**18 // p_i
        else:
            # calculate real prices
            __xp: List[int] = _xp.copy()
            dx_price: int = __xp[0] // 10**6
            __xp[0] += dx_price
            last_prices = [
                price_scale[k - 1]
                * dx_price
                // (__xp[k] - self._newton_y(A, gamma, __xp, D_unadjusted, k))
                for k in range(1, n_coins)
            ]

        self.last_prices = last_prices

        total_supply: int = self.tokens
        old_xcp_profit: int = self.xcp_profit
        old_virtual_price: int = self.virtual_price

        # Update profit numbers without price adjustment first
        xp: List[int] = [D_unadjusted // n_coins] + [
            D_unadjusted * PRECISION // (n_coins * price) for price in price_scale
        ]
        xcp_profit: int = 10**18
        virtual_price: int = 10**18

        if old_virtual_price > 0:
            xcp: int = _geometric_mean(xp, True)
            virtual_price = 10**18 * xcp // total_supply

            if virtual_price < old_virtual_price:
                raise CryptoPoolError("Loss")

            xcp_profit = old_xcp_profit * virtual_price // old_virtual_price

        self.xcp_profit = xcp_profit

        norm: int = 0
        ratio: int = 0
        for k in range(n_coins - 1):
            ratio = price_oracle[k] * 10**18 // price_scale[k]
            ratio = abs(ratio - 10**18)
            norm += ratio**2
        norm = isqrt(norm)

        adjustment_step: int = max(self.adjustment_step, norm // 5)

        needs_adjustment: bool = self.not_adjusted
        # if not needs_adjustment and
        # (virtual_price-10**18 > (xcp_profit-10**18)/2 + self.allowed_extra_profit):
        # (re-arranged for gas efficiency)
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

        if needs_adjustment and norm > adjustment_step and old_virtual_price > 0:
            new_prices = [
                (p * (norm - adjustment_step) + adjustment_step * p_oracle) // norm
                for p, p_oracle in zip(price_scale, price_oracle)
            ]

            # Calculate balances*prices
            xp = [_xp[0]] + [
                balance * p_new // p
                for balance, p, p_new in zip(_xp[1:], price_scale, new_prices)
            ]

            # Calculate "extended constant product" invariant xCP and virtual price
            D: int = self._newton_D(A, gamma, xp)
            xp = [D // n_coins] + [
                D * PRECISION // (n_coins * p_new) for p_new in new_prices
            ]
            new_virtual_price = 10**18 * _geometric_mean(xp, True) // total_supply

            # Proceed if we've got enough profit:
            #   new_virtual_price > 10**18
            #   new_virtual_price - 10**18 > (xcp_profit - 10**18) / 2
            if (new_virtual_price > 10**18) and (
                2 * new_virtual_price - 10**18 > xcp_profit
            ):
                self.price_scale = new_prices
                self.D = D
                self.virtual_price = new_virtual_price
                return

        # If we are here, the price_scale adjustment did not happen
        # Still need to update the profit counter and D
        self.D = D_unadjusted
        self.virtual_price = virtual_price

        # norm appeared < adjustment_step after
        if needs_adjustment:
            self.not_adjusted = False
            self._claim_admin_fees()

    def _claim_admin_fees(self):
        # no gulping logic needed for the python code
        xcp_profit: int = self.xcp_profit
        xcp_profit_a: int = self.xcp_profit_a

        vprice: int = self.virtual_price

        if xcp_profit > xcp_profit_a:
            fees: int = (xcp_profit - xcp_profit_a) * self.admin_fee // (2 * 10**10)
            if fees > 0:
                frac: int = vprice * 10**18 // (vprice - fees) - 10**18
                d_supply = self.tokens * frac // 10**18
                self.tokens += d_supply
                xcp_profit -= fees * 2
                self.xcp_profit = xcp_profit

        A = self.A
        gamma = self.gamma
        totalSupply = self.tokens

        D: int = self._newton_D(A, gamma, self._xp())
        self.D = D
        self.virtual_price = 10**18 * self._get_xcp(D) // totalSupply

        if xcp_profit > xcp_profit_a:
            self.xcp_profit_a = xcp_profit

    def get_dy(self, i: int, j: int, dx: int) -> int:
        """
        Calculate the amount received from swapping `dx`
        amount of the `i`-th coin for the `j`-th coin.

        Parameters
        ----------
        i: int
            Index of 'in' coin
        j: int
            Index of 'out' coin
        dx: int
            Amount of 'in' coin
        Returns
        -------
        int
            The 'out' coin amount

        Note
        ----
        This is a "view" function; it doesn't change the state of the pool.
        """
        assert i != j  # dev: same input and output coin
        assert i < self.n  # dev: coin index out of range
        assert j < self.n  # dev: coin index out of range

        xp: List[int] = self.balances.copy()
        xp[i] += dx
        xp = self._xp_mem(xp)

        A = self.A
        gamma = self.gamma
        D: int = self.D

        y: int = self._newton_y(A, gamma, xp, D, j)
        dy: int = xp[j] - y - 1
        xp[j] = y
        precisions: List[int] = self.precisions
        price_scale: List[int] = self.price_scale
        if j > 0:
            dy = dy * PRECISION // (price_scale[j - 1] * precisions[j])
        else:
            dy = dy // precisions[0]
        dy -= self._fee(xp) * dy // 10**10

        return dy

    def _fee(self, xp: List[int]) -> int:
        """
        f = fee_gamma / (fee_gamma + (1 - K))
        where
        K = prod(x) / (sum(x) / N)**N
        (all normalized to 1e18)
        """
        n_coins: int = self.n
        fee_gamma: int = self.fee_gamma
        if n_coins == 2:
            f: int = xp[0] + xp[1]
            f = (
                fee_gamma
                * 10**18
                // (
                    fee_gamma
                    + 10**18
                    - (10**18 * n_coins**n_coins) * xp[0] // f * xp[1] // f
                )
            )
        else:
            _sum_xp: int = sum(xp)
            K = 10**18
            for _x in xp:
                K = K * n_coins * _x // _sum_xp
            f = fee_gamma * 10**18 // (fee_gamma + 10**18 - K)
        return (self.mid_fee * f + self.out_fee * (10**18 - f)) // 10**18

    def _exchange(
        self,
        i: int,
        j: int,
        dx: int,
        min_dy: int,
    ) -> int:
        assert i != j  # dev: coin index out of range
        assert i < self.n  # dev: coin index out of range
        assert j < self.n  # dev: coin index out of range
        assert dx > 0  # dev: do not exchange 0 coins

        A = self.A
        gamma = self.gamma
        xp: List[int] = self.balances.copy()
        ix: int = j
        p: int = 0
        dy: int = 0

        y: int = xp[j]
        x0: int = xp[i]
        xp[i] = x0 + dx
        self.balances[i] = xp[i]

        xp = self._xp_mem(xp)

        dy = xp[j] - self._newton_y(A, gamma, xp, self.D, j)
        xp[j] -= dy
        dy -= 1

        price_scale: int = self.price_scale[j - 1]
        prec_i: int = self.precisions[i]
        prec_j: int = self.precisions[j]

        if j > 0:
            dy = dy * PRECISION // (price_scale)
        dy = dy // prec_j

        fee = self._fee(xp) * dy // 10**10
        dy -= fee
        assert dy >= min_dy, "Slippage"
        y -= dy

        self.balances[j] = y

        y *= prec_j
        if j > 0:
            y = y * price_scale // PRECISION
        xp[j] = y

        # Calculate price
        if dx > 10**5 and dy > 10**5:
            _dx: int = dx * prec_i
            _dy: int = dy * prec_j
            if i != 0 and j != 0:
                p = self.last_prices[i - 1] * _dx // _dy
            elif i == 0:
                p = _dx * 10**18 // _dy
            else:  # j == 0
                p = _dy * 10**18 // _dx
                ix = i

        self._tweak_price(A, gamma, xp, ix, p, 0)

        return dy, fee

    def exchange(
        self,
        i: int,
        j: int,
        dx: int,
        min_dy: int = 0,
    ) -> int:
        """
        Swap `dx` amount of the `i`-th coin for the `j`-th coin.

        Parameters
        ----------
        i: int
            'In' coin index
        j: int
            'Out' coin index
        dx: int
            'In' coin amount
        min_dy: int, optional
            Minimum 'out' coin amount required (default = 0)

        Returns
        -------
        (int, int)
            (amount of coin `j` received, trading fee)

        Note
        -----
        In the vyper contract, there is an option to exchange using WETH or ETH.
        """
        return self._exchange(
            i,
            j,
            dx,
            min_dy,
        )

    def exchange_underlying(
        self,
        i: int,
        j: int,
        dx: int,
        min_dy: int = 0,
    ) -> int:
        """
        In the vyper contract, this exchanges using ETH instead of WETH.
        In Curvesim, this is the same as `exchange`.
        """
        return self.exchange(i, j, dx, min_dy)

    def add_liquidity(
        self,
        amounts: List[int],
        min_mint_amount: int = 0,
    ) -> int:
        """
        Add liquidity into the pool by depositing coins for LP tokens.

        Parameters
        ----------
        amounts: List[int]
            Deposit amounts.  At least one coin amount must be nonzero.
        min_mint_amount: int
            Minimum amount of LP tokens required (default = 0)

        Returns
        -------
        int
            Amount of LP tokens minted.
        """
        assert amounts[0] > 0 or amounts[1] > 0  # dev: no coins to add

        A = self.A
        gamma = self.gamma
        n_coins: int = self.n

        xp_old: List[int] = self._xp_mem(self.balances)

        for i in range(n_coins):
            self.balances[i] += amounts[i]

        xp: List[int] = self._xp_mem(self.balances)
        amountsp: List[int] = [xp[i] - xp_old[i] for i in range(n_coins)]

        old_D: int = self.D
        D: int = self._newton_D(A, gamma, xp)

        d_token: int = 0
        token_supply: int = self.tokens
        if old_D > 0:
            d_token = token_supply * D // old_D - token_supply
        else:
            # sets initial virtual price to 1
            d_token = self._get_xcp(D)
        assert d_token > 0  # dev: nothing minted

        d_token_fee: int = 0
        if old_D > 0:
            d_token_fee = self._calc_token_fee(amountsp, xp) * d_token // 10**10 + 1
            d_token -= d_token_fee
            token_supply += d_token
            self.tokens += d_token

            # Calculate price:
            # p_i * (dx_i - dtoken / token_supply * xx_i)
            # = sum{k!=i}(p_k * (dtoken / token_supply * xx_k - dx_k))
            # only ix is nonzero
            p: int = 0
            ix: int = -1
            if d_token > 10**5:
                nonzero_indices = [i for i, a in enumerate(amounts) if a != 0]
                if len(nonzero_indices) == 1:
                    # not reached in current tests, which never have nonzero amounts
                    prec: List[int] = self.precisions
                    last_prices: List[int] = self.last_prices
                    balances: List[int] = self.balances

                    ix = amounts.index(0)
                    S: int = 0
                    for i in range(n_coins):
                        if i == ix:
                            continue

                        if i == 0:
                            S += balances[i] * prec[i]
                        else:
                            S += balances[i] * prec[i] * last_prices[i - 1] // PRECISION
                    S = S * d_token // token_supply
                    p = (
                        S
                        * PRECISION
                        // (
                            amounts[ix] * prec[ix]
                            - d_token * balances[ix] * prec[ix] // token_supply
                        )
                    )

            self._tweak_price(A, gamma, xp, ix, p, D)

        else:
            self.D = D
            self.virtual_price = 10**18
            self.xcp_profit = 10**18
            self.tokens += d_token

        assert d_token >= min_mint_amount, "Slippage"

        return d_token

    def _calc_token_fee(self, amounts: List[int], xp: List[int]) -> int:
        n_coins: int = self.n
        # fee = sum(amounts_i - avg(amounts)) * fee' / sum(amounts)
        fee: int = self._fee(xp) * n_coins // (4 * (n_coins - 1))
        S: int = sum(amounts)
        avg: int = S // n_coins
        Sdiff: int = sum(abs(_x - avg) for _x in amounts)
        return fee * Sdiff // S + NOISE_FEE

    def remove_liquidity(
        self,
        _amount: int,
        min_amounts=None,
    ):
        """
        Remove liquidity (burn LP tokens) to receive back part (or all) of
        the deposited funds.

        Parameters
        ----------
        _amount: int
            Amount LP tokens to burn.
        min_amounts: List[int], optional
            Minimum required amounts for each coin.  Default is 0 each.

        Note
        ----
        "This withdrawal method is very safe, does no complex math"
        """
        min_amounts = min_amounts or [0, 0]

        total_supply: int = self.tokens
        self.tokens -= _amount
        balances: List[int] = self.balances
        amount: int = _amount - 1  # Make rounding errors favoring other LPs a tiny bit

        for i in range(self.n):
            d_balance: int = balances[i] * amount // total_supply
            assert d_balance >= min_amounts[i]
            self.balances[i] = balances[i] - d_balance

        D: int = self.D
        self.D = D - D * amount // total_supply

    def remove_liquidity_one_coin(
        self, token_amount: int, i: int, min_amount: int
    ) -> int:
        """
        Remove liquidity entirely in one type of coin.
        Fees will be extracted and there may be significant price impact incurred.

        Parameters
        ----------
        token_amount: int
            Amount of LP tokens to burn.
        i: int
            Index of the `out` coin.
        min_amount: int
            Minimum amount of the 'out' coin required (default = 0)

        Returns
        -------
        int
            Amount of the `i`-th coin received.
        """
        A = self.A
        gamma = self.gamma

        dy: int = 0
        D: int = 0
        p: int = 0
        xp = [0] * self.n
        dy, p, D, xp = self._calc_withdraw_one_coin(
            A, gamma, token_amount, i, False, True
        )
        assert dy >= min_amount, "Slippage"

        self.balances[i] -= dy
        self.tokens -= token_amount

        self._tweak_price(A, gamma, xp, i, p, D)

        return dy

    def _calc_withdraw_one_coin(
        self,
        A: int,
        gamma: int,
        token_amount: int,
        i: int,
        update_D: bool,
        calc_price: bool,
    ) -> (int, int, int, List[int]):
        token_supply: int = self.tokens
        assert token_amount <= token_supply  # dev: token amount more than supply
        assert i < self.n  # dev: coin out of range

        xx: List[int] = self.balances.copy()
        D0: int = 0
        precisions: List[int] = self.precisions

        xp: List[int] = self._xp_mem(xx)

        if update_D:
            D0 = self._newton_D(A, gamma, xp)
        else:
            D0 = self.D

        D: int = D0

        # Charge fee on D, not on y, e.g. reducing invariant LESS than charging user
        fee: int = self._fee(xp)
        dD: int = token_amount * D // token_supply
        D -= dD - (fee * dD // (2 * 10**10) + 1)
        y: int = self._newton_y(A, gamma, xp, D, i)
        if i == 0:
            dy: int = (xp[i] - y) // precisions[i]
        else:
            dy: int = (
                (xp[i] - y) * PRECISION // (precisions[i] * self.price_scale[i - 1])
            )
        xp[i] = y

        # FIXME: update for n coins
        # Price calc
        p: int = 0
        if calc_price and dy > 10**5 and token_amount > 10**5:
            # p_i = dD / D0 * sum'(p_k * x_k) / (dy - dD / D0 * y0)
            S: int = 0
            precision: int = precisions[0]
            if i == 1:
                S = xx[0] * precisions[0]
                precision = precisions[1]
            else:
                S = xx[1] * precisions[1]
            S = S * dD // D0
            p = S * PRECISION // (dy * precision - dD * xx[i] * precision // D0)
            if i == 0:
                p = (10**18) ** 2 // p

        return dy, p, D, xp

    def calc_withdraw_one_coin(self, token_amount: int, i: int) -> int:
        """
        Calculate the output amount from burning `token amount` of LP tokens
        and receiving entirely in the `i`-th coin.

        Parameters
        ----------
        token_amount: int
            Amount of LP tokens to burn.
        i: int
            Index of the `out` coin.

        Returns
        -------
        int
            Output amount of the `i`-th coin.
        """
        return self._calc_withdraw_one_coin(
            self.A, self.gamma, token_amount, i, True, False
        )[0]

    def lp_price(self) -> int:
        """
        Returns an LP token price approximating behavior as a constant-product AMM.
        """
        if self.n == 2:
            price_oracle = self.internal_price_oracle()[0]
            return 2 * self.virtual_price * _sqrt_int(price_oracle) // 10**18
        # TODO: find/implement integer cube root function
        # elif self.n == 3:
        #     price_oracle = self.internal_price_oracle()
        #     return (
        #         3 * self.virtual_price * icbrt(price_oracle[0] * price_oracle[1])
        #     ) // 10**24
        else:
            raise CalculationError("LP price calc doesn't support more than 3 coins")

    def internal_price_oracle(self) -> List[int]:
        """
        Return the value of the EMA price oracle.
        """
        price_oracle: int = self._price_oracle
        last_prices_timestamp: int = self.last_prices_timestamp

        block_timestamp: int = self._block_timestamp
        if last_prices_timestamp < block_timestamp:
            ma_half_time: int = self.ma_half_time
            last_prices: int = self.last_prices
            alpha: int = _halfpow(
                (block_timestamp - last_prices_timestamp) * 10**18 // ma_half_time
            )
            return [
                (last_p * (10**18 - alpha) + oracle_p * alpha) // 10**18
                for last_p, oracle_p in zip(last_prices, price_oracle)
            ]

        return price_oracle

    def price_oracle(self) -> List[int]:
        """
        Return the value of the EMA price oracle.

        Same as `internal_price_oracle`.  Kept for compatability with the
        vyper interface.
        """
        return self.internal_price_oracle()

    def get_virtual_price(self) -> int:
        """
        Return the virtual price of an LP token.
        """
        return 10**18 * self._get_xcp(self.D) // self.tokens

    def calc_token_amount(self, amounts: List[int]) -> int:
        """
        Calculate the amount of LP tokens minted by depositing given amounts.

        Parameters
        ----------
        amounts: List[int]
            Deposit amounts.  At least one coin amount must be nonzero.

        Returns
        -------
        int
            Amount of LP tokens minted.
        """
        token_supply: int = self.tokens
        A = self.A
        gamma = self.gamma
        xp: List[int] = self._xp()
        amountsp = self._xp_mem(amounts)
        D0: int = self.D
        for i, a in enumerate(amountsp):
            xp[i] += a
        D: int = self._newton_D(A, gamma, xp)
        d_token: int = token_supply * D // D0 - token_supply
        d_token -= self._calc_token_fee(amountsp, xp) * d_token // 10**10 + 1
        return d_token


def _get_unix_timestamp():
    """Get the timestamp in Unix time."""
    return int(time.time())


def _geometric_mean(unsorted_x: List[int], sort: bool) -> int:
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
        if n_coins == 2:
            D = (D + x[0] * x[1] // D) // n_coins
        else:
            tmp: int = 10**18
            for _x in x:
                tmp = tmp * _x // D
            D = D * ((n_coins - 1) * 10**18 + tmp) // (n_coins * 10**18)
        diff = abs(D_prev - D)
        if diff <= 1 or diff * 10**18 < D:
            return int(D)
    raise CalculationError("Did not converge")


def _halfpow(power: int) -> int:
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
