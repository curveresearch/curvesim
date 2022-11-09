"""
Mainly a module to house the `Pool`, a basic stableswap implementation in Python.
"""
from math import prod

from gmpy2 import mpz

from ..base import Pool


class CurvePool(Pool):
    """
    Basic stableswap implementation in Python.
    """

    def __init__(
        self,
        A,
        D,
        n,
        p=None,
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
            coin balances or virtual total balance
        n: int
            number of coins
        p: list of int
            precision and rate adjustments
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
        p = p or [10**18] * n

        if isinstance(D, list):
            x = D
        else:
            x = [D // n * 10**18 // _p for _p in p]

        self.A = A
        self.n = n
        self.fee = fee
        self.p = p
        self.x = x
        self.tokens = tokens or self.D()
        self.fee_mul = fee_mul
        self.admin_fee = admin_fee
        self.r = False
        self.n_total = n
        self.admin_balances = [0] * n

    @property
    def balances(self):
        """
        Alias to adhere closer to vyper interface.

        Returns
        -------
        list of int
            pool coin balances in native token units
        """
        return self.x

    def next_timestamp(self, *args, **kwargs):
        pass

    def _xp(self):
        return [x * p // 10**18 for x, p in zip(self.x, self.p)]

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
        xp = xp or self._xp()
        return self.get_D(xp, A)

    def get_D(self, xp, A):
        """
        Calculate D invariant iteratively using non-overflowing integer operations.

        Stableswap equation:

        .. math::
             A n^n \sum{x_i} + D = A n^n D + D^{n+1} / (n^n \prod{x_i})

        Converging solution using Newton's method:

        .. math::
             d_{j+1} = (A n^n \sum{x_i} + n d_j^{n+1} / (n^n \prod{x_i}))
                     / (A n^n + (n+1) d_j^n/(n^n \prod{x_i}) - 1)

        Replace :math:`A n^n` by `An` and :math:`d_j^{n+1}/(n^n \prod{x_i})` by :math:`D_p` to
        arrive at the iterative formula in the code.

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
        n = self.n
        Ann = self.A * n
        D = mpz(D)
        Ann = mpz(Ann)
        while abs(D - Dprev) > 1:
            D_P = D
            for x in xp:
                D_P = D_P * D // (n * x)
            Dprev = D
            D = (Ann * S + D_P * n) * D // ((Ann - 1) * D + (n + 1) * D_P)

        D = int(D)
        return D

    def get_D_mem(self, balances, A):
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
        xp = [x * p // 10**18 for x, p in zip(balances, self.p)]
        return self.get_D(xp, A)

    def get_y(self, i, j, x, xp):
        """
        Calculate x[j] if one makes x[i] = x.

        The stableswap equation gives the following:

        .. math::
            x_1^2 + x_1 (\operatorname{sum'} - (A n^n - 1) D / (A n^n))
               = D^{n+1}/(n^{2 * n} \operatorname{prod'} A)

        where :math:`\operatorname{sum'}` is the sum of all :math:`x_i` for :math:`i \\neq j` and
        :math:`\operatorname{prod'}` is the product of all :math:`x_i` for :math:`i \\neq j`.

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
            The balance of the j-th coin, in units of D, for the other coin balances given.

        Note
        ----
        This is a "view" function; it doesn't change the state of the pool.
        """  # noqa
        xx = xp[:]
        D = self.D(xx)
        D = mpz(D)
        xx[i] = x  # x is quantity of underlying asset brought to 1e18 precision
        n = self.n
        xx = [xx[k] for k in range(n) if k != j]
        Ann = self.A * n
        c = D
        for y in xx:
            c = c * D // (y * n)
        c = c * D // (n * Ann)
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
        n = self.n
        xx = [xp[k] for k in range(n) if k != i]
        S = sum(xx)
        Ann = A * n
        c = D
        for y in xx:
            c = c * D // (y * n)
        c = c * D // (n * Ann)
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

        >>> pool = Pool(A=250, D=1000000 * 10**18, n=2, p=[10**30, 10**30])
        >>> pool.exchange(0, 1, 150 * 10**6)
        (149939820, 59999)
        """
        xp = self._xp()
        x = xp[i] + dx * self.p[i] // 10**18
        y = self.get_y(i, j, x, xp)
        dy = xp[j] - y - 1

        if self.fee_mul is None:
            fee = dy * self.fee // 10**10
        else:
            fee = dy * self.dynamic_fee((xp[i] + x) // 2, (xp[j] + y) // 2) // 10**10

        admin_fee = fee * self.admin_fee // 10**10

        # Convert all to real units
        rate = self.p[j]
        dy = (dy - fee) * 10**18 // rate
        fee = fee * 10**18 // rate
        admin_fee = admin_fee * 10**18 // rate
        assert dy >= 0

        self.x[i] += dx
        self.x[j] -= dy + admin_fee
        self.admin_balances[j] += admin_fee
        return dy, fee

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
        xp = self._xp()
        D0 = self.D()
        D1 = D0 - token_amount * D0 // self.tokens

        new_y = self.get_y_D(A, i, xp, D1)
        dy_before_fee = (xp[i] - new_y) * 10**18 // self.p[i]

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
        dy = (dy - 1) * 10**18 // self.p[i]
        if use_fee:
            dy_fee = dy_before_fee - dy
            return dy, dy_fee
        else:
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

        balances = self.x
        afee = self.admin_fee
        admin_fees = [f * afee // 10**10 for f in fees]
        new_balances = [
            bal + amt - fee for bal, amt, fee in zip(balances, amounts, admin_fees)
        ]
        self.x = new_balances
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
        self.x[i] -= dy + admin_fee
        self.admin_balances[i] += admin_fee
        self.tokens -= token_amount
        return dy, dy_fee

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
        old_balances = self.x
        D0 = self.get_D_mem(old_balances, A)

        new_balances = self.x[:]
        for i in range(self.n):
            new_balances[i] += amounts[i]
        D1 = self.get_D_mem(new_balances, A)

        mint_balances = new_balances[:]

        if use_fee:
            _fee = self.fee * self.n // (4 * (self.n - 1))

            fees = [0] * self.n
            for i in range(self.n):
                ideal_balance = D1 * old_balances[i] // D0
                difference = abs(ideal_balance - new_balances[i])
                fees[i] = _fee * difference // 10**10
                mint_balances[i] -= fees[i]

        D2 = self.get_D_mem(mint_balances, A)

        mint_amount = self.tokens * (D2 - D0) // D0
        if use_fee:
            return mint_amount, fees
        else:
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
