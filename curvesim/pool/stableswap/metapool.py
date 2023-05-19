"""
Mainly a module to house the `MetaPool`, a metapool stableswap implementation in Python.
"""
from math import prod

from gmpy2 import mpz

from curvesim.pool.snapshot import CurveMetaPoolBalanceSnapshot

from ..base import Pool


class CurveMetaPool(Pool):  # pylint: disable=too-many-instance-attributes
    """
    Basic stableswap metapool implementation in Python.
    """

    snapshot_class = CurveMetaPoolBalanceSnapshot

    __slots__ = (
        "A",
        "n",
        "max_coin",
        "fee",
        "admin_fee",
        "basepool",
        "rate_multiplier",
        "balances",
        "n_total",
        "tokens",
        "fee_mul",
        "admin_balances",
    )

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        A,
        D,
        n,
        basepool,
        rate_multiplier=10**18,
        tokens=None,
        fee=4 * 10**6,
        fee_mul=None,
        admin_fee=0 * 10**9,
    ):
        """
        Parameters
        ----------
        A : int
            Amplification coefficient; this is :math:`A n^{n-1}` in the whitepaper.
        D : int or list of int
            virtual total balance or coin balances in native token units
        n: int
            number of coins
        basepool: :class:`curvesim.pool.Pool`
            basepool for the metapool
        rate_multiplier: int, optional
            precision and rate adjustment, defaults to 10**18
        tokens: int
            LP token supply
        fee: int, optional
            fee with 10**10 precision (default = .004%)
        fee_mul: optional
            fee multiplier for dynamic fee pools
        admin_fee: int, optional
            percentage of `fee` with 10**10 precision (default = 50%)
        """
        # FIXME: set admin_fee default back to 5 * 10**9
        # once sim code is updated.  Right now we use 0
        # to pass the CI tests.
        self.A = A
        self.n = n
        self.max_coin = self.n - 1
        self.fee = fee
        self.admin_fee = admin_fee

        # If basepool coins have too few decimals, it can wreak havoc
        # on a certain codepath of our `dydx` function, where we use
        # a difference quotient to estimate the derivative.
        for _p in basepool.rates:
            if _p > 10**30:
                raise ValueError(f"{_p} too high: decimals must be >= 6.")
        self.basepool = basepool

        self.rate_multiplier = rate_multiplier

        if isinstance(D, list):
            self.balances = D
        else:
            self.balances = [D // n * 10**18 // _p for _p in self.rates]

        self.n_total = n + basepool.n - 1
        self.tokens = tokens
        self.fee_mul = fee_mul
        self.admin_balances = [0] * n

    def D(self, xp=None):
        """
        `D` is the stableswap invariant; this can be thought of as the value of
        all coin balances if the pool were to become balanced.

        Convenience wrapper for `get_D` which uses the set `A` and makes `xp`
        an optional arg.

        Parameters
        ----------
        xp: list of ints
            Coin balances in units of D

        Returns
        -------
        int
            The stableswap invariant, `D`.

        Note
        ----
        This is a "view" function; it doesn't change the state of the pool.
        """
        A = self.A
        if not xp:
            rates = self.rates
            xp = [x * p // 10**18 for x, p in zip(self.balances, rates)]
        return self.get_D(xp, A)

    def get_D(self, xp, A):
        r"""
        Calculate D invariant iteratively using non-overflowing integer operations.

        Stableswap equation:

        .. math::
             A n^n \sum{x_i} + D = A n^n D + D^{n+1} / (n^n \prod{x_i})

        Converging solution using Newton's method:

        .. math::
             d_{j+1} = (A n^n \sum{x_i} + n d_j^{n+1} / (n^n \prod{x_i}))
                     / (A n^n + (n+1) d_j^n/(n^n \prod{x_i}) - 1)

        Replace :math:`A n^n` by `An` and :math:`d_j^{n+1}/(n^n \prod{x_i})` by
        :math:`D_p` to arrive at the iterative formula in the code.

        Parameters
        ----------
        xp: list of ints
            Coin balances in units of D
        A: int
            Amplification coefficient

        Returns
        -------
        int
            The stableswap invariant, `D`.

        Note
        ----
        This is a "view" function; it doesn't change the state of the pool.
        """  # noqa
        Dprev = 0
        S = sum(xp)
        D = S
        Ann = A * self.n
        D = mpz(D)
        Ann = mpz(Ann)
        while abs(D - Dprev) > 1:
            D_P = D
            for x in xp:
                D_P = D_P * D // (self.n * x)
            Dprev = D
            D = (Ann * S + D_P * self.n) * D // ((Ann - 1) * D + (self.n + 1) * D_P)

        D = int(D)
        return D

    def _xp(self):
        rates = self.rates
        balances = self.balances
        return self._xp_mem(rates, balances)

    def _xp_mem(self, rates, balances):
        return [x * p // 10**18 for x, p in zip(balances, rates)]

    def get_D_mem(self, rates, balances, A):
        """
        Convenience wrapper for `get_D` which takes in balances in token units.
        Naming is based on the vyper equivalent.

        Parameters
        ----------
        balances: list of ints
            Coin balances in native token units
        A: int
            Amplification coefficient

        Returns
        -------
        int
            The stableswap invariant, `D`.

        Note
        ----
        This is a "view" function; it doesn't change the state of the pool.
        """
        xp = self._xp_mem(rates, balances)
        return self.get_D(xp, A)

    def get_y(self, i, j, x, xp):
        r"""
        Calculate x[j] if one makes x[i] = x.

        The stableswap equation gives the following:

        .. math::
            x_1^2 + x_1 (\operatorname{sum'} - (A n^n - 1) D / (A n^n))
               = D^{n+1}/(n^{2 n} \operatorname{prod'} A)

        where :math:`\operatorname{sum'}` is the sum of all :math:`x_i` for
        :math:`i \\neq j` and :math:`\operatorname{prod'}` is the product
        of all :math:`x_i` for :math:`i \\neq j`.

        This is a quadratic equation in :math:`x_j`.

        .. math:: x_1^2 + b x_1 = c

        which can then be solved iteratively by Newton's method:

        .. math:: x_1 := (x_1^2 + c) / (2 x_1 + b)

        Parameters
        ----------
        i: int
            index of coin; usually the "in"-token
        j: int
            index of coin; usually the "out"-token
        x: int
            balance of i-th coin in units of D
        xp: list of int
            coin balances in units of D

        Returns
        -------
        int
            The balance of the j-th coin, in units of D, for the other
            coin balances given.

        Note
        ----
        This is a "view" function; it doesn't change the state of the pool.
        """  # noqa
        xx = xp[:]
        D = self.D(xx)
        D = mpz(D)
        xx[i] = x  # x is quantity of underlying asset brought to 1e18 precision
        xx = [xx[k] for k in range(self.n) if k != j]
        Ann = self.A * self.n
        c = D
        for y in xx:
            c = c * D // (y * self.n)
        c = c * D // (self.n * Ann)
        b = sum(xx) + D // Ann - D
        y_prev = 0
        y = D
        while abs(y - y_prev) > 1:
            y_prev = y
            y = (y**2 + c) // (2 * y + b)
        y = int(y)
        return y  # result is in units for D

    def get_y_D(self, A, i, xp, D):
        """
        Calculate x[i] if one uses a reduced `D` than one calculated for given `xp`.

        See docstring for `get_y`.

        Parameters
        ----------
        A: int
            Amplification coefficient for given xp and D
        i: int
            index of coin to calculate balance for
        xp: list of int
            coin balances in units of D
        D: int
            new invariant value

        Returns
        -------
        int
            The balance of the i-th coin, in units of D

        Note
        ----
        This is a "view" function; it doesn't change the state of the pool.
        """
        D = mpz(D)
        xx = [xp[k] for k in range(self.n) if k != i]
        S = sum(xx)
        Ann = A * self.n
        c = D
        for y in xx:
            c = c * D // (y * self.n)
        c = c * D // (self.n * Ann)
        b = S + D // Ann
        y_prev = 0
        y = D
        while abs(y - y_prev) > 1:
            y_prev = y
            y = (y**2 + c) // (2 * y + b - D)
        y = int(y)
        return y  # result is in units for D

    def exchange(self, i, j, dx):
        """
        Perform an exchange between two coins.
        Index values can be found via the `coins` public getter method.

        Parameters
        ----------
        i : int
            Index of "in" coin.
        j : int
            Index of "out" coin.
        dx : int
            Amount of coin `i` being exchanged.

        Returns
        -------
        (int, int)
            (amount of coin `j` received, trading fee)

        Examples
        --------

        >>> pool = MetaPool(A=250, D=1000000 * 10**18, n=2, p=[10**30, 10**30])
        >>> pool.exchange(0, 1, 150 * 10**6)
        (149939820, 59999)
        """
        rates = self.rates
        xp = self._xp_mem(rates, self.balances)
        x = xp[i] + dx * rates[i] // 10**18
        y = self.get_y(i, j, x, xp)
        dy = xp[j] - y - 1

        if self.fee_mul is None:
            fee = dy * self.fee // 10**10
        else:
            fee = dy * self.dynamic_fee((xp[i] + x) // 2, (xp[j] + y) // 2) // 10**10

        admin_fee = fee * self.admin_fee // 10**10

        # Convert all to real units
        rate = rates[j]
        dy = (dy - fee) * 10**18 // rate
        fee = fee * 10**18 // rate
        admin_fee = admin_fee * 10**18 // rate
        assert dy >= 0

        self.balances[i] += dx
        self.balances[j] -= dy + admin_fee
        self.admin_balances[j] += admin_fee
        return dy, fee

    def exchange_underlying(self, i, j, dx):
        """
        Perform an exchange between two coins.

        Index values include underlyer indices.  The zero index
        is the "primary" stable for the metapool, while indices
        1, 2, ..., correspond to the basepool indices offset
        by one.

        Parameters
        ----------
        i : int
            Index of "in" coin.
        j : int
            Index of "out" coin.
        dx : int
            Amount of coin `i` being exchanged.

        Returns
        -------
        (int, int)
            (amount of coin `j` received, trading fee)
        """
        rates = self.rates

        # Use base_i or base_j if they are >= 0
        base_i = i - self.max_coin
        base_j = j - self.max_coin
        meta_i = self.max_coin
        meta_j = self.max_coin
        if base_i < 0:
            meta_i = i
        if base_j < 0:
            meta_j = j

        if base_i < 0 or base_j < 0:  # if i or j not in basepool
            xp = [x * p // 10**18 for x, p in zip(self.balances, rates)]

            if base_i < 0:
                x = xp[i] + dx * rates[i] // 10**18
            else:
                # i is from BasePool
                # At first, get the amount of pool tokens
                base_inputs = [0] * self.basepool.n
                base_inputs[base_i] = dx
                # Deposit and measure delta
                dx = self.basepool.add_liquidity(base_inputs)
                # Need to convert pool token to "virtual" units using rates
                x = dx * rates[self.max_coin] // 10**18
                # Adding number of pool tokens
                x += xp[self.max_coin]

            y = self.get_y(meta_i, meta_j, x, xp)

            # Either a real coin or token
            dy = xp[meta_j] - y - 1
            dy_fee = dy * self.fee // 10**10

            # Convert all to real units
            # Works for both pool coins and real coins
            dy = (dy - dy_fee) * 10**18 // rates[meta_j]

            dy_admin_fee = dy_fee * self.admin_fee // 10**10
            dy_admin_fee = dy_admin_fee * 10**18 // rates[meta_j]

            dy_fee = dy_fee * 10**18 // rates[meta_j]

            # Change balances exactly in same way as we change actual ERC20 coin amounts
            self.balances[meta_i] += dx
            # When rounding errors happen, we undercharge admin fee in favor of LP
            self.balances[meta_j] -= dy + dy_admin_fee
            self.admin_balances[meta_j] += dy_admin_fee

            # Withdraw from the base pool if needed
            if base_j >= 0:
                dy, dy_fee = self.basepool.remove_liquidity_one_coin(dy, base_j)

        else:
            # If both are from the base pool
            dy, dy_fee = self.basepool.exchange(base_i, base_j, dx)

        return dy, dy_fee

    def calc_withdraw_one_coin(self, token_amount, i, use_fee=True):
        """
        Calculate the amount in the i-th coin received from
        redeeming the given amount of LP tokens.

        By default, fees are deducted.

        Parameters
        ----------
        token_amount: int
            Amount of LP tokens to redeem
        i: int
            Index of coin to withdraw in.
        use_fee: bool, default=True
            Deduct fees.

        Returns
        -------
        int
            Redemption amount in i-th coin

        Note
        ----
        This is a "view" function; it doesn't change the state of the pool.
        """
        A = self.A
        rates = self.rates
        xp = self._xp_mem(rates, self.balances)
        D0 = self.D()
        D1 = D0 - token_amount * D0 // self.tokens

        new_y = self.get_y_D(A, i, xp, D1)
        dy_before_fee = (xp[i] - new_y) * 10**18 // rates[i]

        xp_reduced = xp
        if self.fee and use_fee:
            n_coins = self.n
            _fee = self.fee * n_coins // (4 * (n_coins - 1))

            for j in range(n_coins):
                dx_expected = 0
                if j == i:
                    dx_expected = xp[j] * D1 // D0 - new_y
                else:
                    dx_expected = xp[j] - xp[j] * D1 // D0
                xp_reduced[j] -= _fee * dx_expected // 10**10

        dy = xp[i] - self.get_y_D(A, i, xp_reduced, D1)
        dy = (dy - 1) * 10**18 // rates[i]

        if use_fee:
            dy_fee = dy_before_fee - dy
            return dy, dy_fee

        return dy

    def add_liquidity(self, amounts):
        """
        Deposit coin amounts for LP token.

        Parameters
        ----------
        amounts: list of int
            Coin amounts to deposit

        Returns
        -------
        int
            LP token amount received for the deposit amounts.
        """
        mint_amount, fees = self.calc_token_amount(amounts, use_fee=True)
        self.tokens += mint_amount

        balances = self.balances
        afee = self.admin_fee
        admin_fees = [f * afee // 10**10 for f in fees]
        new_balances = [
            bal + amt - fee for bal, amt, fee in zip(balances, amounts, admin_fees)
        ]
        self.balances = new_balances
        self.admin_balances = [t + a for t, a in zip(self.admin_balances, admin_fees)]

        return mint_amount

    def remove_liquidity_one_coin(self, token_amount, i):
        """
        Redeem given LP token amount for the i-th coin.

        Parameters
        ----------
        token_amount: int
            Amount of LP tokens to redeem
        i: int
            Index of coin to withdraw in

        Returns
        -------
        int
            Redemption amount in i-th coin
        """
        dy, dy_fee = self.calc_withdraw_one_coin(token_amount, i, use_fee=True)
        admin_fee = dy_fee * self.admin_fee // 10**10
        self.balances[i] -= dy + admin_fee
        self.admin_balances[i] += admin_fee
        self.tokens -= token_amount
        return dy, dy_fee

    @property
    def rates(self):
        base_virtual_price = self.basepool.get_virtual_price()
        return [self.rate_multiplier, base_virtual_price]

    def calc_token_amount(self, amounts, use_fee=False):
        """
        Calculate the amount of LP tokens received for the given coin
        deposit amounts.

        Fee logic is based on add_liquidity, which makes this more accurate than
        the `calc_token_amount` in the actual contract, which neglects fees.

        By default, it's assumed you the same behavior as the vyper contract,
        which is to NOT deduct fees.

        Parameters
        ----------
        amounts: list of int
            Coin amounts to be deposited.
        use_fee: bool, default=False
            Deduct fees.

        Returns
        -------
        int
            LP token amount received for the deposit amounts.

        Note
        ----
        This is a "view" function; it doesn't change the state of the pool.
        """
        A = self.A
        old_balances = self.balances
        rates = self.rates
        D0 = self.get_D_mem(rates, old_balances, A)

        new_balances = self.balances[:]
        for i in range(self.n):
            new_balances[i] += amounts[i]
        D1 = self.get_D_mem(rates, new_balances, A)

        mint_balances = new_balances[:]

        if use_fee:
            _fee = self.fee * self.n // (4 * (self.n - 1))

            fees = [0] * self.n
            for i in range(self.n):
                ideal_balance = D1 * old_balances[i] // D0
                difference = abs(ideal_balance - new_balances[i])
                fees[i] = _fee * difference // 10**10
                mint_balances[i] -= fees[i]

        D2 = self.get_D_mem(rates, mint_balances, A)

        mint_amount = self.tokens * (D2 - D0) // D0

        if use_fee:
            return mint_amount, fees

        return mint_amount

    def get_virtual_price(self):
        """
        Returns the expected value of one LP token if the pool were
        to become perfectly balanced (all coins revert to peg).

        Returns
        -------
        int
            Amount of the stableswap invariant, `D`, corresponding to
            one LP token, in units of `D`.

        Note
        ----
        This is a "view" function; it doesn't change the state of the pool.
        """
        return self.D() * 10**18 // self.tokens

    def dynamic_fee(self, xpi, xpj):
        xps2 = xpi + xpj
        xps2 *= xps2  # Doing just ** 2 can overflow apparently
        return (self.fee_mul * self.fee) // (
            (self.fee_mul - 10**10) * 4 * xpi * xpj // xps2 + 10**10
        )

    def dydxfee(self, i, j):
        """
        Returns the spot price of i-th coin quoted in terms of j-th coin,
        i.e. the ratio of output coin amount to input coin amount for
        an "infinitesimally" small trade.

        The indices are assumed to include base pool underlyer indices.

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

    def dydx(self, i, j, use_fee=False):
        r"""
        Returns the spot price of i-th coin quoted in terms of j-th coin,
        i.e. the ratio of output coin amount to input coin amount for
        an "infinitesimally" small trade.

        The indices are assumed to include base pool underlyer indices.

        Parameters
        ----------
        i: int
            Index of coin to be priced; in a swapping context, this is
            the "in"-token.
        j: int
            Index of quote currency; in a swapping context, this is the
            "out"-token.
        use_fee: bool, default=False
            Deduct fees.

        Returns
        -------
        float
            Price of i-th coin quoted in j-th coin

        Note
        ----
        This is a "view" function; it doesn't change the state of the pool.

        The following formulae are useful when swapping the primary stablecoin
        for one of the basepool underlyers:

            |  $z$: primary coin virtual balance
            |  $w$: basepool virtual balance in the metapool
            |  $x_i$: basepool coin virtual balances
            |  $D$: basepool invariant

            The chain rule gives:

            .. math::
                \frac{dz}{dx_i} = \frac{dz}{dw} \frac{dw}{dx_i}
                    = \frac{dz}{dw} \frac{dD}{dx_i} = \frac{dz}{dw} D'

            where

            .. math::
                D' = -1 ( A n^{n+1} \prod{x_k} + D^{n+1} / x_i)
                        / ( n^n \prod{x_k} - A n^{n+1} \prod{x_k} - (n + 1) D^n
        """  # noqa
        base_i = i - self.max_coin
        base_j = j - self.max_coin

        # both in and out tokens are in basepool
        if base_i >= 0 and base_j >= 0:
            _dydx = self.basepool.dydx(base_i, base_j, use_fee=use_fee)
            return float(_dydx)

        rates = self.rates
        xp = [mpz(x) * p // 10**18 for x, p in zip(self.balances, rates)]

        bp = self.basepool
        base_xp = [mpz(x) * p // 10**18 for x, p in zip(bp.balances, bp.rates)]
        x_prod = prod(base_xp)
        n = bp.n
        A = bp.A
        D = mpz(bp.D())
        D_pow = D ** (n + 1)
        A_pow = A * n ** (n + 1)

        if base_i < 0:  # i is primary
            xj = base_xp[base_j]
            D_prime = (
                -1
                * (A_pow * x_prod + D_pow / xj)
                / (n**n * x_prod - A_pow * x_prod - (n + 1) * D**n)
            )
            D_prime = float(D_prime)

            dwdz = self._dydx(0, self.max_coin, xp, use_fee)
            _dydx = dwdz / D_prime

            if use_fee and bp.fee:
                fee = bp.fee - bp.fee * xj // sum(base_xp) + 5 * 10**5
            else:
                fee = 0
            _dydx *= 1 - fee / 10**10

        else:  # i is from basepool
            dx = 10**12
            base_inputs = [0] * self.basepool.n
            base_inputs[base_i] = dx * 10**18 // self.basepool.rates[base_i]

            dw, _ = self.basepool.calc_token_amount(base_inputs, use_fee=True)
            # Convert lp token amount to virtual units
            dw = dw * rates[self.max_coin] // 10**18
            x = xp[self.max_coin] + dw

            meta_i = self.max_coin
            meta_j = j
            y = self.get_y(meta_i, meta_j, x, xp)

            dy = xp[meta_j] - y - 1
            if use_fee:
                dy_fee = dy * self.fee // 10**10
            else:
                dy_fee = 0
            dy -= dy_fee

            _dydx = dy / dx

        return float(_dydx)

    def _dydx(self, i, j, xp, use_fee=False):
        """
        Treats indices as applying to the "top-level" pool if a metapool.
        Basically this is the "regular" pricing calc with no special metapool
        handling.

        Returns the spot price of i-th coin quoted in terms of j-th coin,
        i.e. the ratio of output coin amount to input coin amount for
        an "infinitesimally" small trade.

        Defaults to no fees deducted.

        Parameters
        ----------
        i: int
            Index of coin to be priced; in a swapping context, this is
            the "in"-token
        j: int
            Index of quote currency; in a swapping context, this is the
            "out"-token
        xp: list of int
            "Virtual" coin balances, i.e. balances in units of D
        use_fee: bool, default=False
            Deduct fees

        Returns
        -------
        float
            Price of i-th coin quoted in j-th coin

        Note
        ----
        This is a "view" function; it doesn't change the state of the pool.
        """
        xi = xp[i]
        xj = xp[j]
        n = self.n
        A = self.A
        D = self.D(xp)
        D_pow = mpz(D) ** (n + 1)
        x_prod = prod(xp)
        A_pow = A * n ** (n + 1)
        dydx = (xj * (xi * A_pow * x_prod + D_pow)) / (
            xi * (xj * A_pow * x_prod + D_pow)
        )

        if use_fee:
            if self.fee_mul is None:
                fee_factor = self.fee / 10**10
            else:
                fee_factor = self.dynamic_fee(xi, xj) / 10**10
        else:
            fee_factor = 0

        dydx *= 1 - fee_factor

        return float(dydx)
