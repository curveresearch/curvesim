"""
Mainly a module to house the `CryptoPool`, a cryptoswap implementation in Python.
"""
import time
from typing import List

from gmpy2 import mpz

from curvesim.exceptions import CalculationError, CryptoPoolError, CurvesimValueError
from curvesim.pool.base import Pool

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
        price_scale: int,
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
        price_scale: int
            Price scale value for the pool.  This is where liquidity is concentrated.
        price_oracle: int, optional
            Price oracle value for the pool.  This is the EMA price used to
            adjust the price scale toward.
            Defaults to `price_scale`.
        last_prices: int, optional
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

        if n != 2:
            raise CryptoPoolError("Only 2-coin crypto pools are currently supported.")
        self.n = n
        self.precisions = precisions

        if len(precisions) != n:
            raise ValueError("`len(precisions)` must equal `n`")

        if balances is None and D is None:
            raise ValueError("Must provide at least one of `balances` or `D`.")

        if balances:
            self.balances = balances

        if D is not None:
            self.D = D
            if not balances:
                self.balances = [
                    D // n // precisions[0],
                    D * PRECISION // (n * self.price_scale) // precisions[1],
                ]
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

    def _xp(self) -> List[int]:
        """
        Calculate the balances in units of `D`, converting using `price_scale`
        so a unit of each token has equal value.
        """
        precisions = self.precisions
        return [
            self.balances[0] * precisions[0],
            self.balances[1] * precisions[1] * self.price_scale // PRECISION,
        ]

    def _get_xcp(self, D: int) -> int:
        """
        Calculate the constant-product profit, using the balances at
        equilibrium point.
        """
        n_coins: int = self.n
        x: List[int] = [
            D // n_coins,
            D * PRECISION // (self.price_scale * n_coins),
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

        # Initial value of invariant D is that for constant-product invariant
        x: List[int] = x_unsorted
        if x[0] < x[1]:
            x = [x_unsorted[1], x_unsorted[0]]

        assert (
            x[0] > 10**9 - 1 and x[0] < 10**15 * 10**18 + 1
        )  # dev: unsafe values x[0]
        assert x[1] * 10**18 // x[0] > 10**14 - 1  # dev: unsafe values x[i] (input)

        D: int = n_coins * _geometric_mean(x, False)
        S: int = x[0] + x[1]

        D = mpz(D)
        S = mpz(S)
        for _ in range(255):
            D_prev: int = D

            # K0: int = 10**18
            # for _x in x:
            #     K0 = K0 * _x * n_coins / D
            # collapsed for 2 coins
            K0: int = (10**18 * n_coins**2) * x[0] // D * x[1] // D

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
                return int(D)

        raise CalculationError("Did not converge")

    @staticmethod
    def _newton_y(ANN: int, gamma: int, x: List[int], D: int, i: int) -> int:
        """
        Calculating x[i] given other balances x[0..n_coins-1] and invariant D
        ANN = A * N**N
        """
        n_coins: int = len(x)

        # Safety checks
        min_A = n_coins**n_coins * A_MULTIPLIER // 10
        max_A = n_coins**n_coins * A_MULTIPLIER * 100000
        if ANN > max_A or ANN < min_A:
            raise CurvesimValueError("Unsafe value for A")
        if gamma > MAX_GAMMA or gamma < MIN_GAMMA:
            raise CurvesimValueError("Unsafe value for gamma")
        if D > 10**15 * 10**18 or D < 10**17:
            raise CurvesimValueError("Unsafe value for D")

        x_j: int = x[1 - i]
        y: int = D**2 // (x_j * n_coins**2)
        K0_i: int = (10**18 * n_coins) * x_j // D
        # S_i = x_j

        # frac = x_j * 1e18 / D => frac = K0_i / N_COINS
        assert (
            10**16 * n_coins <= K0_i <= 10**20 * n_coins
        )  # dev: unsafe values x[i]

        convergence_limit: int = max(max(x_j // 10**14, D // 10**14), 100)

        y = mpz(y)
        K0_i = mpz(K0_i)
        D = mpz(D)
        for _ in range(255):
            y_prev: int = y

            K0: int = K0_i * y * n_coins // D
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

            diff: int = 0
            if y > y_prev:
                diff = y - y_prev
            else:
                diff = y_prev - y
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
        price_oracle: int = self._price_oracle
        last_prices: int = self.last_prices
        price_scale: int = self.price_scale
        last_prices_timestamp: int = self.last_prices_timestamp
        block_timestamp: int = self._block_timestamp
        p_new: int = 0
        n_coins: int = self.n

        if last_prices_timestamp < block_timestamp:
            # MA update required
            ma_half_time: int = self.ma_half_time
            alpha: int = _halfpow(
                (block_timestamp - last_prices_timestamp) * 10**18 // ma_half_time
            )
            price_oracle = (
                last_prices * (10**18 - alpha) + price_oracle * alpha
            ) // 10**18
            self._price_oracle = price_oracle
            self.last_prices_timestamp = block_timestamp

        D_unadjusted: int = new_D  # Withdrawal methods know new D already
        if new_D == 0:
            # We will need this a few times (35k gas)
            D_unadjusted = self._newton_D(A, gamma, _xp)

        if p_i > 0:
            last_prices = p_i

        else:
            # calculate real prices
            __xp: List[int] = _xp.copy()
            dx_price: int = __xp[0] // 10**6
            __xp[0] += dx_price
            last_prices = (
                price_scale
                * dx_price
                // (_xp[1] - self._newton_y(A, gamma, __xp, D_unadjusted, 1))
            )

        self.last_prices = last_prices

        total_supply: int = self.tokens
        old_xcp_profit: int = self.xcp_profit
        old_virtual_price: int = self.virtual_price

        # Update profit numbers without price adjustment first
        xp: List[int] = [
            D_unadjusted // n_coins,
            D_unadjusted * PRECISION // (n_coins * price_scale),
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

        norm: int = price_oracle * 10**18 // price_scale
        norm = abs(norm - 10**18)
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
            p_new = (
                price_scale * (norm - adjustment_step) + adjustment_step * price_oracle
            ) // norm

            # Calculate balances*prices
            xp = [_xp[0], _xp[1] * p_new // price_scale]

            # Calculate "extended constant product" invariant xCP and virtual price
            D: int = self._newton_D(A, gamma, xp)
            xp = [D // n_coins, D * PRECISION // (n_coins * p_new)]
            new_virtual_price = 10**18 * _geometric_mean(xp, True) // total_supply

            # Proceed if we've got enough profit:
            #   new_virtual_price > 10**18
            #   new_virtual_price - 10**18 > (xcp_profit - 10**18) / 2
            if (new_virtual_price > 10**18) and (
                2 * new_virtual_price - 10**18 > xcp_profit
            ):
                self.price_scale = p_new
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
        precisions: List[int] = self.precisions
        price_scale: int = self.price_scale * precisions[1]
        xp = [xp[0] * precisions[0], xp[1] * price_scale // PRECISION]

        A = self.A
        gamma = self.gamma
        D: int = self.D

        y: int = self._newton_y(A, gamma, xp, D, j)
        dy: int = xp[j] - y - 1
        xp[j] = y
        if j > 0:
            dy = dy * PRECISION // price_scale
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
        f: int = xp[0] + xp[1]  # sum
        f = (
            fee_gamma
            * 10**18
            // (
                fee_gamma
                + 10**18
                - (10**18 * n_coins**n_coins) * xp[0] // f * xp[1] // f
            )
        )
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
        p: int = 0
        dy: int = 0

        y: int = xp[j]
        x0: int = xp[i]
        xp[i] = x0 + dx
        self.balances[i] = xp[i]

        price_scale: int = self.price_scale
        precisions: List[int] = self.precisions

        xp = [xp[0] * precisions[0], xp[1] * price_scale * precisions[1] // PRECISION]

        prec_i: int = precisions[0]
        prec_j: int = precisions[1]
        if i == 1:
            prec_i = precisions[1]
            prec_j = precisions[0]

        dy = xp[j] - self._newton_y(A, gamma, xp, self.D, j)
        xp[j] -= dy
        dy -= 1

        if j > 0:
            dy = dy * PRECISION // price_scale
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
            if i == 0:
                p = _dx * 10**18 // _dy
            else:  # j == 0
                p = _dy * 10**18 // _dx

        self._tweak_price(A, gamma, xp, p, 0)

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

        xp: List[int] = self.balances.copy()
        amountsp: List[int] = [0] * n_coins
        xx: List[int] = [0] * n_coins
        d_token: int = 0
        d_token_fee: int = 0
        old_D: int = 0

        xp_old: List[int] = xp.copy()

        for i in range(n_coins):
            bal: int = xp[i] + amounts[i]
            xp[i] = bal
            self.balances[i] = bal
        xx = xp.copy()

        precisions: List[int] = self.precisions

        price_scale: int = self.price_scale * precisions[1]
        xp = [xp[0] * precisions[0], xp[1] * price_scale // PRECISION]
        xp_old = [xp_old[0] * precisions[0], xp_old[1] * price_scale // PRECISION]

        for i in range(n_coins):
            if amounts[i] > 0:
                amountsp[i] = xp[i] - xp_old[i]

        old_D = self.D
        D: int = self._newton_D(A, gamma, xp)

        token_supply: int = self.tokens
        if old_D > 0:
            d_token = token_supply * D // old_D - token_supply
        else:
            d_token = self._get_xcp(D)  # making initial virtual price equal to 1
        assert d_token > 0  # dev: nothing minted

        if old_D > 0:
            d_token_fee = self._calc_token_fee(amountsp, xp) * d_token // 10**10 + 1
            d_token -= d_token_fee
            token_supply += d_token
            self.tokens += d_token

            # Calculate price:
            # p_i * (dx_i - dtoken / token_supply * xx_i)
            # = sum{k!=i}(p_k * (dtoken / token_supply * xx_k - dx_k))
            # (simplified for 2 coins)
            p: int = 0
            if d_token > 10**5:
                if amounts[0] == 0 or amounts[1] == 0:
                    S: int = 0
                    precision: int = 0
                    ix: int = 0
                    if amounts[0] == 0:
                        S = xx[0] * precisions[0]
                        precision = precisions[1]
                        ix = 1
                    else:
                        S = xx[1] * precisions[1]
                        precision = precisions[0]
                    S = S * d_token // token_supply
                    p = (
                        S
                        * PRECISION
                        // (
                            amounts[ix] * precision
                            - d_token * xx[ix] * precision // token_supply
                        )
                    )
                    if ix == 0:
                        p = (10**18) ** 2 // p

            self._tweak_price(A, gamma, xp, p, D)

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
        S: int = 0
        for _x in amounts:
            S += _x
        avg: int = S // n_coins
        Sdiff: int = 0
        for _x in amounts:
            if _x > avg:
                Sdiff += _x - avg
            else:
                Sdiff += avg - _x
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

        self._tweak_price(A, gamma, xp, p, D)

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

        price_scale_i: int = self.price_scale * precisions[1]
        xp: List[int] = [
            xx[0] * precisions[0],
            xx[1] * price_scale_i // PRECISION,
        ]
        if i == 0:
            price_scale_i = PRECISION * precisions[0]

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
        dy: int = (xp[i] - y) * PRECISION // price_scale_i
        xp[i] = y

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
        return (
            2 * self.virtual_price * _sqrt_int(self.internal_price_oracle()) // 10**18
        )

    def internal_price_oracle(self) -> int:
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
            return (last_prices * (10**18 - alpha) + price_oracle * alpha) // 10**18

        return price_oracle

    def price_oracle(self) -> int:
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
        precisions: List[int] = self.precisions
        price_scale: int = self.price_scale * precisions[1]
        A = self.A
        gamma = self.gamma
        xp: List[int] = self._xp()
        amountsp: List[int] = [
            amounts[0] * precisions[0],
            amounts[1] * price_scale // PRECISION,
        ]
        D0: int = self.D
        xp[0] += amountsp[0]
        xp[1] += amountsp[1]
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
    if sort and x[0] < x[1]:
        x = [unsorted_x[1], unsorted_x[0]]

    D: int = mpz(x[0])
    diff: int = 0
    for _ in range(255):
        D_prev: int = D
        # tmp: uint256 = 10**18
        # for _x in x:
        #     tmp = tmp * _x / D
        # D = D * ((N_COINS - 1) * 10**18 + tmp) / (N_COINS * 10**18)
        # line below makes it for 2 coins
        D = (D + x[0] * x[1] // D) // n_coins
        if D > D_prev:
            diff = D - D_prev
        else:
            diff = D_prev - D
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
