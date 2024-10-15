"""
Mainly a module to house the `CurveCryptoPool`, a cryptoswap implementation in Python.
"""
import time
from math import isqrt, prod
from typing import List, Optional, Tuple, Type

from curvesim.exceptions import CalculationError, CryptoPoolError, CurvesimValueError
from curvesim.logging import get_logger
from curvesim.pool.base import Pool
from curvesim.pool.snapshot import CurveCryptoPoolBalanceSnapshot, Snapshot

from .calcs import (
    factory_2_coin,
    geometric_mean,
    get_alpha,
    get_p,
    get_y,
    newton_D,
    tricrypto_ng,
)

logger = get_logger(__name__)

NOISE_FEE = 10**5  # 0.1 bps
EXP_PRECISION = 10**10
PRECISION = 10**18


class CurveCryptoPool(Pool):  # pylint: disable=too-many-instance-attributes
    """Cryptoswap implementation in Python."""

    snapshot_class: Type[Snapshot] = CurveCryptoPoolBalanceSnapshot

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

    # pylint: disable-next=too-many-locals,too-many-arguments,too-many-branches
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
        last_prices_timestamp=None,
        balances=None,
        D=None,
        tokens=None,
        admin_fee: int = 5 * 10**9,
        xcp_profit=10**18,
        xcp_profit_a=10**18,
        virtual_price=None,
    ) -> None:
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
        last_prices_timestamp: int, optional
            Timestamp for last operation altering pool price.
            Defaults to unix timestamp.
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
        virtual_price: int, optional
            amount of XCP invariant per LP token; can be used when
            missing `tokens` value.
        """
        self.A = A
        self.gamma = gamma

        self.mid_fee = mid_fee
        self.out_fee = out_fee
        self.allowed_extra_profit = allowed_extra_profit
        self.fee_gamma = fee_gamma
        self.adjustment_step = adjustment_step
        self.admin_fee = admin_fee

        self.price_scale = price_scale.copy()
        self._price_oracle = price_oracle.copy() if price_oracle else price_scale.copy()
        self.last_prices = last_prices.copy() if last_prices else price_scale.copy()
        self.ma_half_time = ma_half_time

        self._block_timestamp = _get_unix_timestamp()
        self.last_prices_timestamp = last_prices_timestamp or 0

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
            self.balances = balances.copy()

        if D is not None:
            self.D = D
            if not balances:
                self.balances = self._convert_D_to_balances(D)
            else:
                # If user passes both `D` and `balances`, it's possible they may
                # be inconsistent; however we allow this for unanticipated use-cases.
                logger.debug(
                    "Both `D` and `balances` were passed into `__init__`. "
                    "Inconsistent values may create issues."
                )
        else:
            xp = self._xp()
            D = newton_D(A, gamma, xp)
            self.D = D

        if tokens and virtual_price:
            raise CurvesimValueError(
                "Should not set both `tokens` and `virtual_price`."
            )

        xcp = self._get_xcp(D)
        if virtual_price:
            self.virtual_price = virtual_price
            self.tokens = xcp * 10**18 // virtual_price
        else:
            if tokens:
                self.tokens = tokens
            else:
                self.tokens = xcp
            self.virtual_price = 10**18 * xcp // self.tokens

    def _convert_D_to_balances(self, D):
        price_scale = self.price_scale
        precisions = self.precisions
        n = self.n

        return [D // n // precisions[0]] + [
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
        This intentionally always returns a new copy of the balances.
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
        return geometric_mean(x)

    def _increment_timestamp(self, blocks=1, timestamp=None) -> None:
        """Update the internal clock used to mimic the block timestamp."""
        if timestamp:
            self._block_timestamp = timestamp
            return

        self._block_timestamp += 12 * blocks

    # pylint: disable-next=R0912,R0913,R0914,R0915
    def _tweak_price(  # noqa: complexity: 12
        self,
        A: int,
        gamma: int,
        _xp: List[int],
        i: int,
        p_i: Optional[int],
        new_D: int,
        K0_prev: int = 0,
    ) -> None:
        """
        Applies several kinds of updates:
            - EMA price update: price_oracle
            - Profit counters: D, virtual_price, xcp_profit
            - price adjustment: price_scale
                - If p_i is None, the spot price will be used as the last price

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
            alpha: int = get_alpha(
                ma_half_time, block_timestamp, last_prices_timestamp, n_coins
            )
            if n_coins == 2:
                price_oracle = [
                    (last_p * (10**18 - alpha) + oracle_p * alpha) // 10**18
                    for last_p, oracle_p in zip(last_prices, price_oracle)
                ]
            elif n_coins == 3:
                # Cap state price that goes into the EMA with 2*price_scale.
                price_oracle = [
                    (min(last_p, 2 * p) * (10**18 - alpha) + oracle_p * alpha)
                    // 10**18
                    for last_p, oracle_p, p in zip(
                        last_prices, price_oracle, price_scale
                    )
                ]
            else:
                raise CalculationError("More than 3 coins is not supported.")
            self._price_oracle = price_oracle
            self.last_prices_timestamp = block_timestamp

        D_unadjusted: int = new_D  # Withdrawal methods know new D already
        if new_D == 0:
            D_unadjusted = newton_D(A, gamma, _xp, K0_prev)

        if p_i is None:
            if n_coins == 2:
                # calculate real prices
                __xp: List[int] = _xp.copy()
                dx_price: int = __xp[0] // 10**6
                __xp[0] += dx_price
                last_prices = [
                    price_scale[k - 1]
                    * dx_price
                    // (
                        __xp[k]
                        - factory_2_coin.newton_y(A, gamma, __xp, D_unadjusted, k)
                    )
                    for k in range(1, n_coins)
                ]
            else:
                last_prices = get_p(_xp, D_unadjusted, A, gamma)
                last_prices = [
                    last_p * p // 10**18
                    for last_p, p in zip(last_prices, price_scale)
                ]
        elif p_i > 0:
            # Save the last price
            if i > 0:
                last_prices[i - 1] = p_i
            else:
                # If 0th price changed - change all prices instead
                for k in range(n_coins - 1):
                    last_prices[k] = last_prices[k] * 10**18 // p_i
        else:
            raise CalculationError(f"p_i (last price) cannot be {p_i}.")

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
            xcp: int = geometric_mean(xp)
            virtual_price = 10**18 * xcp // total_supply

            if virtual_price < old_virtual_price:
                raise CryptoPoolError("Loss")

            xcp_profit = old_xcp_profit * virtual_price // old_virtual_price

        self.xcp_profit = xcp_profit

        if virtual_price * 2 - 10**18 > xcp_profit + 2 * self.allowed_extra_profit:
            norm: int = 0
            ratio: int = 0
            for k in range(n_coins - 1):
                ratio = price_oracle[k] * 10**18 // price_scale[k]
                ratio = abs(ratio - 10**18)
                norm += ratio**2
            norm = isqrt(norm)
            adjustment_step: int = max(self.adjustment_step, norm // 5)

            if norm > adjustment_step:
                new_prices = [
                    (p * (norm - adjustment_step) + adjustment_step * p_oracle) // norm
                    for p, p_oracle in zip(price_scale, price_oracle)
                ]

                # Calculate balances * prices
                xp = [_xp[0]] + [
                    balance * p_new // p
                    for balance, p, p_new in zip(_xp[1:], price_scale, new_prices)
                ]

                # Calculate "extended constant product" invariant xCP and virtual price
                D: int = newton_D(A, gamma, xp)
                xp = [D // n_coins] + [
                    D * PRECISION // (n_coins * p_new) for p_new in new_prices
                ]
                new_virtual_price = 10**18 * geometric_mean(xp) // total_supply

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

    def _claim_admin_fees(self) -> None:
        """
        If the pool's profit has increased since the last fee claim, update profit,
        pool value, and LP token supply to reflect the admin taking its share of the
        fees by minting itself LP tokens. Otherwise, change nothing.

        Tricrypto-NG and Cryptopool implement this functionality differently, so we
        copy only Tricrypto-NG's way in this class for consistency.
        """
        # no gulping logic needed for the python code
        A: int = self.A
        gamma: int = self.gamma

        xcp_profit: int = self.xcp_profit
        xcp_profit_a: int = self.xcp_profit_a
        total_supply: int = self.tokens

        if xcp_profit <= xcp_profit_a or total_supply < 10**18:
            return

        vprice: int = self.virtual_price

        fees: int = (xcp_profit - xcp_profit_a) * self.admin_fee // (2 * 10**10)

        if fees > 0:
            frac: int = vprice * 10**18 // (vprice - fees) - 10**18
            d_supply: int = total_supply * frac // 10**18
            self.tokens += d_supply
            xcp_profit -= fees * 2
            self.xcp_profit = xcp_profit

        D: int = newton_D(A, gamma, self._xp())
        self.D = D

        self.virtual_price = 10**18 * self._get_xcp(D) // self.tokens
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

        A: int = self.A
        gamma: int = self.gamma
        D: int = self.D

        y: int = get_y(A, gamma, xp, D, j)[0]
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

    def get_y(self, i: int, j: int, x: int, xp: List[int]) -> int:
        r"""
        Calculate x[j] if one makes x[i] = x.

        Parameters
        ----------
        i: int
            index of coin; usually the "in"-token
        j: int
            index of coin; usually the "out"-token
        x: int
            balance of i-th coin in units of `D`
        xp: list of int
            coin balances in units of `D`

        Returns
        -------
        int
            The balance of the j-th coin, in units of `D`, for the other
            coin balances given.

        Note
        ----
        This is a "view" function; it doesn't change the state of the pool.
        """
        A: int = self.A
        gamma: int = self.gamma
        D: int = newton_D(A, gamma, xp)

        xp = xp.copy()
        xp[i] = x

        y, _ = get_y(A, gamma, xp, D, j)
        return y

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
            K: int = 10**18
            for _x in xp:
                K = K * n_coins * _x // _sum_xp
            f = fee_gamma * 10**18 // (fee_gamma + 10**18 - K)
        return (self.mid_fee * f + self.out_fee * (10**18 - f)) // 10**18

    # pylint: disable-next=too-many-locals
    def _exchange(
        self,
        i: int,
        j: int,
        dx: int,
        min_dy: int,
    ) -> Tuple[int, int]:
        assert i != j, "Indices must be different"
        assert i < self.n, "Index out of bounds"
        assert j < self.n, "Index out of bounds"
        assert dx > 0, "Can't swap zero amount"

        A = self.A
        gamma = self.gamma
        xp: List[int] = self.balances.copy()
        ix: int = j

        y: int = xp[j]
        xp[i] += dx
        self.balances[i] = xp[i]

        xp = self._xp_mem(xp)

        y_out = get_y(A, gamma, xp, self.D, j)
        dy: int = xp[j] - y_out[0]
        assert dy >= 0, f"Invalid dy: dx: {dx}, dy: {dy}, i: {i}, j: {j} "
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
        assert dy >= min_dy, f"Slippage: dy: {dy}"
        y -= dy

        self.balances[j] = y

        y *= prec_j
        if j > 0:
            y = y * price_scale // PRECISION
        xp[j] = y

        p: Optional[int] = None
        K0_prev: int = 0
        if self.n == 2:
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
        else:
            K0_prev = y_out[1]

        self._tweak_price(A, gamma, xp, ix, p, 0, K0_prev)

        return dy, fee

    def exchange(
        self,
        i: int,
        j: int,
        dx: int,
        min_dy: int = 0,
    ) -> Tuple[int, int]:
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
        return self._exchange(i, j, dx, min_dy)

    def exchange_underlying(
        self,
        i: int,
        j: int,
        dx: int,
        min_dy: int = 0,
    ) -> Tuple[int, int]:
        """
        In the vyper contract, this exchanges using ETH instead of WETH.
        In Curvesim, this is the same as `exchange`.
        """
        return self.exchange(i, j, dx, min_dy)

    # pylint: disable-next=too-many-locals, too-many-statements
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
        assert all(x >= 0 for x in amounts)
        assert sum(amounts) > 0

        A = self.A
        gamma = self.gamma
        n_coins: int = self.n

        xp_old: List[int] = self._xp_mem(self.balances)

        for i in range(n_coins):
            self.balances[i] += amounts[i]

        xp: List[int] = self._xp_mem(self.balances)
        amountsp: List[int] = [xp[i] - xp_old[i] for i in range(n_coins)]

        old_D: int = self.D
        D: int = newton_D(A, gamma, xp)

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

            p: Optional[int] = None
            ix: int = -1
            if n_coins == 2 and d_token > 10**5:
                nonzero_indices = [i for i, a in enumerate(amounts) if a != 0]
                if len(nonzero_indices) == 1:
                    # Calculate price for 2 coins:
                    # p_i * (dx_i - dtoken / token_supply * xx_i)
                    # = sum{k!=i}(p_k * (dtoken / token_supply * xx_k - dx_k))
                    # only ix is nonzero
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
            self.xcp_profit_a = 10**18
            self.tokens += d_token

        assert d_token >= min_mint_amount, "Slippage"

        self._claim_admin_fees()

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
    ) -> List[int]:
        """
        Remove liquidity (burn LP tokens) to receive back part (or all) of
        the deposited funds.

        Parameters
        ----------
        _amount: int
            Amount LP tokens to burn.
        min_amounts: List[int], optional
            Minimum required amounts for each coin.  Default is 0 each.

        Returns
        -------
        List[int]
            The amounts of each coin received.

        Note
        ----
        "This withdrawal method is very safe, does no complex math"
        """
        n_coins: int = self.n
        min_amounts = min_amounts or [0] * n_coins

        amount: int = _amount
        balances: List[int] = self.balances
        withdraw_amounts: List[int] = [0] * n_coins

        self._claim_admin_fees()

        total_supply: int = self.tokens
        assert amount <= total_supply
        self.tokens -= amount

        if amount != total_supply:
            amount -= 1  # Make rounding errors favor other LPs a tiny bit

        for i in range(n_coins):
            withdraw_amounts[i] = balances[i] * amount // total_supply
            assert withdraw_amounts[i] >= min_amounts[i]
            self.balances[i] = balances[i] - withdraw_amounts[i]

        D: int = self.D
        self.D = D - D * amount // total_supply

        return withdraw_amounts

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
        A: int = self.A
        gamma: int = self.gamma

        dy: int = 0
        D: int = 0
        p: Optional[int] = None
        xp: List[int] = [0] * self.n

        self._claim_admin_fees()

        calc_price: bool = self.n == 2

        dy, p, D, xp = self._calc_withdraw_one_coin(
            A, gamma, token_amount, i, False, calc_price
        )
        assert dy >= min_amount, "Slippage"

        self.balances[i] -= dy
        self.tokens -= token_amount

        self._tweak_price(A, gamma, xp, i, p, D)

        return dy

    # pylint: disable-next=too-many-locals,too-many-arguments, too-many-branches
    def _calc_withdraw_one_coin(
        self,
        A: int,
        gamma: int,
        token_amount: int,
        i: int,
        update_D: bool,
        calc_price: bool,
    ) -> Tuple[int, Optional[int], int, List[int]]:
        """
        Calculate the output amount from burning `token amount` of LP tokens
        and receiving entirely in the `i`-th coin.

        Parameters
        ----------
        A: int
            Amplification coefficient equal to `A * n**n` from the whitepaper.
        gamma: int
            Gamma coefficient from the whitepaper.
        token_amount: int
            Amount of LP tokens to burn.
        i: int
            Index of the `out` coin.
        update_D: bool
            Switch for recomputing `D` during calculation.
        calc_price: bool
            Switch for recomputing the price of token `i` after simulating a
            withdrawal. Only does something if `n` = 2.

        Returns
        -------
        int
            Output amount of the `i`-th coin.
        Optional[int]
            Price of the `i`-th coin after the withdrawal.
        int
            `D` after the withdrawal, accounting for fee.
        List[int]
            `xp` after the withdrawal, accounting for fee.

        Note
        ----
        The 3-coin pool contract doesn't have calc_price even though the 2-coin one
        does, so the price value returned is `None` when the price calculation doesn't
        occur.

        This is a "view" function; it doesn't change the state of the pool.
        """
        token_supply: int = self.tokens
        assert token_amount <= token_supply
        assert i < self.n, "Index out of bounds"

        xx: List[int] = self.balances.copy()
        precisions: List[int] = self.precisions

        xp: List[int] = self._xp_mem(xx)

        if update_D:
            D0: int = newton_D(A, gamma, xp)
        else:
            D0 = self.D

        D: int = D0

        if self.n == 2:
            fee: int = self._fee(xp)
        elif self.n == 3:
            # For n = 3, charge max fee if xp_correction > xp_imprecise[i]
            # Specifically, if % of xp[i] withdrawn > 1/n = 1/3
            # Otherwise, _fee() underflows
            n_coins: int = self.n
            xp_imprecise: List[int] = xp.copy()
            xp_correction: int = xp[i] * n_coins * token_amount // token_supply

            if xp_correction < xp_imprecise[i]:
                xp_imprecise[i] -= xp_correction
                fee = self._fee(xp_imprecise)
            else:
                fee = self.out_fee
        else:
            raise CalculationError(
                "_calc_withdraw_one_coin doesn't support more than 3 coins"
            )

        # Charge fee on D, not on y, e.g. reducing invariant LESS than charging user
        dD: int = token_amount * D // token_supply
        D_fee: int = fee * dD // (2 * 10**10) + 1
        D -= dD - D_fee
        y: int = get_y(A, gamma, xp, D, i)[0]
        if i == 0:
            dy: int = (xp[i] - y) // precisions[i]
        else:
            dy = (xp[i] - y) * PRECISION // (precisions[i] * self.price_scale[i - 1])
        xp[i] = y

        # Price calc
        p: Optional[int] = None
        if self.n == 2 and calc_price:
            if dy > 10**5 and token_amount > 10**5:
                # p_i = dD / D0 * sum'(p_k * x_k) / (dy - dD / D0 * y0)
                j = (i + 1) % 2
                precision: int = precisions[i]
                S: int = xx[j] * precisions[j]
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

        Note
        ----
        This is a "view" function; it doesn't change the state of the pool.
        """
        return self._calc_withdraw_one_coin(
            self.A, self.gamma, token_amount, i, True, False
        )[0]

    def lp_price(self) -> int:
        """
        Returns the price of an LP token in units of token 0.

        Derived from the equilibrium point of a constant-product AMM
        that approximates Cryptoswap's behavior.

        Returns
        -------
        int
            Liquidity redeemable per LP token in units of token 0.

        Note
        ----
        This is a "view" function; it doesn't change the state of the pool.
        """
        if self.n == 2:
            virtual_price: int = self.virtual_price
            price_oracle: List[int] = self.internal_price_oracle()
            price: int = factory_2_coin.lp_price(virtual_price, price_oracle)
        elif self.n == 3:
            # 3-coin vyper contract uses cached packed oracle prices
            # instead of internal_price_oracle()
            virtual_price = self.virtual_price
            price_oracle = self._price_oracle
            price = tricrypto_ng.lp_price(virtual_price, price_oracle)
        else:
            raise CalculationError("LP price calc doesn't support more than 3 coins")

        return price

    def internal_price_oracle(self) -> List[int]:
        """
        Return the value of the EMA price oracle.
        """
        price_oracle: List[int] = self._price_oracle
        last_prices_timestamp: int = self.last_prices_timestamp

        block_timestamp: int = self._block_timestamp
        if last_prices_timestamp < block_timestamp:

            if self.n == 2:
                last_prices: List[int] = self.last_prices
            elif self.n == 3:
                # 3-coin vyper contract caps every "last price" that gets fed to the EMA
                last_prices = self.last_prices.copy()
                price_scale: List[int] = self.price_scale
                last_prices = [
                    min(last_p, 2 * storage_p)
                    for last_p, storage_p in zip(last_prices, price_scale)
                ]
            else:
                raise CalculationError(
                    "Price oracle calc doesn't support more than 3 coins"
                )

            ma_half_time: int = self.ma_half_time
            n_coins: int = self.n
            alpha: int = get_alpha(
                ma_half_time, block_timestamp, last_prices_timestamp, n_coins
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

        Note
        ----
        This is a "view" function; it doesn't change the state of the pool.
        """
        token_supply: int = self.tokens
        A: int = self.A
        gamma: int = self.gamma
        xp: List[int] = self._xp()
        amountsp: List[int] = self._xp_mem(amounts)
        D0: int = self.D

        for i, a in enumerate(amountsp):
            xp[i] += a

        D: int = newton_D(A, gamma, xp)
        d_token: int = token_supply * D // D0 - token_supply
        d_token -= self._calc_token_fee(amountsp, xp) * d_token // 10**10 + 1

        return d_token

    def dydxfee(self, i, j):
        """
        Returns the spot price of i-th coin quoted in terms of j-th coin,
        i.e. the ratio of output coin amount to input coin amount for
        an "infinitesimally" small trade.

        Trading fees are deducted.

        Parameters
        ----------
        i: int
            Index of coin to be priced; in a swapping context, this is
            the "in"-token.
        j: int
            Index of quote currency; in a swapping context, this is the
            "out"-token.

        Returns
        -------
        float
            Price of i-th coin quoted in j-th coin with fees deducted.

        Note
        ----
        This is a "view" function; it doesn't change the state of the pool.
        """
        return self.dydx(i, j, use_fee=True)

    def dydx(self, i, j, use_fee=False):  # pylint: disable=too-many-locals
        """
        Returns the spot price of i-th coin quoted in terms of j-th coin,
        i.e. the ratio of output coin amount to input coin amount for
        an "infinitesimally" small trade.

        Defaults to no fees deducted.

        Parameters
        ----------
        i: int
            Index of coin to be priced; in a swapping context, this is
            the "in"-token.
        j: int
            Index of quote currency; in a swapping context, this is the
            "out"-token.

        Returns
        -------
        float
            Price of i-th coin quoted in j-th coin

        Note
        ----
        This is a "view" function; it doesn't change the state of the pool.
        """
        xp = self._xp()
        x_i = xp[i]
        x_j = xp[j]
        n = len(xp)

        D = self.D
        A = self.A
        A_multiplier = 10**4
        gamma = self.gamma

        K0 = 10**18 * n**n * prod(xp) / D**n

        coeff = A * gamma**2 / (10**18 + gamma - K0) ** 2
        frac = (10**18 + gamma + K0) * (sum(xp) - D) / (10**18 + gamma - K0)
        dydx_top = x_j * (A_multiplier * D + coeff * (x_i + frac))
        dydx_bottom = x_i * (A_multiplier * D + coeff * (x_j + frac))
        dydx = dydx_top / dydx_bottom

        if j > 0:
            price_scale = self.price_scale[j - 1]
            dydx = dydx * 10**18 / price_scale
        if i > 0:
            price_scale = self.price_scale[i - 1]
            dydx = dydx * price_scale / 10**18

        if use_fee:
            fee = self._fee(xp)
            dydx = dydx - dydx * fee / 10**10

        return dydx


def _get_unix_timestamp():
    """Get the timestamp in Unix time."""
    return int(time.time())
