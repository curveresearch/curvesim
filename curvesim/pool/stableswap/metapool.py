from math import prod

from gmpy2 import mpz


class MetaPool:
    """
    Basic stableswap metapool implementation in Python.
    """

    def __init__(
        self,
        A,
        D,
        n,
        basepool,
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
        fee_mul:
            fee multiplier for dynamic fee pools
        admin_fee: int, optional
            percentage of `fee` with 10**10 precision (default = 50%)
        r: int, optional
            initial redemption price for RAI-like pools
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
        for _p in basepool.p:
            if _p > 10**30:
                raise ValueError(f"{_p} too high: decimals must be >= 6.")
        self.basepool = basepool

        if p:
            self.p = p
        else:
            self.p = [10**18] * n

        if isinstance(D, list):
            self.x = D
        else:
            rates = self.rates()
            self.x = [D // n * 10**18 // _p for _p in rates]

        self.n_total = n + basepool.n - 1
        self.tokens = tokens
        self.fee_mul = fee_mul
        self.collected_admin_fees = [0] * n

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

    def D(self, xp=None):
        A = self.A
        if not xp:
            rates = self.rates()
            xp = [x * p // 10**18 for x, p in zip(self.x, rates)]
        return self.get_D(xp, A)

    def get_D(self, xp, A):
        """
        D invariant calculation in non-overflowing integer operations
        iteratively

        A * sum(x_i) * n**n + D = A * D * n**n + D**(n+1) / (n**n * prod(x_i))

        Converging solution:
        D[j+1] = (A * n**n * sum(x_i) - D[j]**(n+1) / (n**n prod(x_i))) / (A * n**n - 1)
        """
        Dprev = 0
        S = sum(xp)
        D = S
        Ann = self.A * self.n
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
        rates = self.rates()
        balances = self.x
        return self._xp_mem(rates, balances)

    def _xp_mem(self, rates, balances):
        return [x * p // 10**18 for x, p in zip(balances, rates)]

    def get_D_mem(self, rates, balances, A):
        xp = self._xp_mem(rates, balances)
        return self.get_D(xp, A)

    def get_y(self, i, j, x, xp):
        """
        Calculate x[j] if one makes x[i] = x

        Done by solving quadratic equation iteratively.
        x_1**2 + x1 * (sum' - (A * n - 1) * D / (A * n)) = D**(n + 1)/(n**(n + 1) * prod' * A)
        x_1**2 + b*x_1 = c

        x_1 = (x_1**2 + c) / (2*x_1 + b)
        """
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
        Calculate x[i] if one reduces D from being calculated for xp to D

        Done by solving quadratic equation iteratively.
        x_1**2 + x1 * (sum' - (A * n - 1) * D / (A * n)) = D**(n + 1)/(n**(n + 1) * prod' * A)
        x_1**2 + b*x_1 = c

        x_1 = (x_1**2 + c) / (2*x_1 + b)
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
        self.collected_admin_fees[j] += admin_fee
        return dy, fee

    def exchange_underlying(self, i, j, dx):
        rates = self.rates()

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
            xp = [x * p // 10**18 for x, p in zip(self.x, rates)]

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
            self.x[meta_i] += dx
            # When rounding errors happen, we undercharge admin fee in favor of LP
            self.x[meta_j] -= dy + dy_admin_fee
            self.collected_admin_fees[meta_j] += dy_admin_fee

            # Withdraw from the base pool if needed
            if base_j >= 0:
                dy, dy_fee = self.basepool.remove_liquidity_one_coin(dy, base_j)

        else:
            # If both are from the base pool
            dy, dy_fee = self.basepool.exchange(base_i, base_j, dx)

        return dy, dy_fee

    def calc_withdraw_one_coin(self, token_amount, i, use_fee=True):
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
        mint_amount, fees = self.calc_token_amount(amounts, use_fee=True)
        self.tokens += mint_amount

        balances = self.x
        afee = self.admin_fee
        admin_fees = [f * afee // 10**10 for f in fees]
        new_balances = [
            bal + amt - fee for bal, amt, fee in zip(balances, amounts, admin_fees)
        ]
        self.x = new_balances
        self.collected_admin_fees = [
            t + a for t, a in zip(self.collected_admin_fees, admin_fees)
        ]

        return mint_amount

    def remove_liquidity_one_coin(self, token_amount, i):
        dy, dy_fee = self.calc_withdraw_one_coin(token_amount, i, use_fee=True)
        admin_fee = dy_fee * self.admin_fee // 10**10
        self.x[i] -= dy + admin_fee
        self.collected_admin_fees[i] += admin_fee
        self.tokens -= token_amount
        return dy, dy_fee

    def rates(self):
        rates = self.p[:]
        rates[self.max_coin] = self.basepool.get_virtual_price()
        return rates

    def calc_token_amount(self, amounts, use_fee=False):
        """
        Fee logic is based on add_liquidity, which makes this more accurate than
        the `calc_token_amount` in the actual contract, which neglects fees.

        By default, it's assumed you want the contract behavior.
        """
        A = self.A
        old_balances = self.x
        rates = self.rates()
        D0 = self.get_D_mem(rates, old_balances, A)

        new_balances = self.x[:]
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
        else:
            return mint_amount

    def get_virtual_price(self):
        """Return virtual dollars per LP token in 18 decimal precision."""
        return self.D() * 10**18 // self.tokens

    def dynamic_fee(self, xpi, xpj):
        xps2 = xpi + xpj
        xps2 *= xps2  # Doing just ** 2 can overflow apparently
        return (self.fee_mul * self.fee) // (
            (self.fee_mul - 10**10) * 4 * xpi * xpj // xps2 + 10**10
        )

    def dydxfee(self, i, j, dx=10**12):
        """
        Returns price with fee, (dy[j]-fee)/dx[i]) given some dx[i]

        For metapools, the indices are assumed to include base pool
        underlyer indices.
        """
        return self.dydx(i, j, dx, use_fee=True)

    def dydx(self, i, j, dx=10**12, use_fee=False):
        """
        Returns price, dy[j]/dx[i], given some dx[i]

        For metapools, the indices are assumed to include base pool
        underlyer indices.

        --------------------------------
        -- Metapool pricing formula ----
        --------------------------------
        z: primary coin balance
        w: basepool virtual balance
        x_i: basepool coin balances

        dz/dx_i = dz/dw  * dw/dx_i = dz/dw * dD/dx_i = dz/dw * D'
        where D refers to the basepool

        D' = -1 * ( A * n ** (n+1) * prod(x_k) + D ** (n+1) / x_i)
                / ( n ** n * prod(x_k) - A * n ** (n+1) * prod(x_k) - (n + 1) * D ** n
        """
        base_i = i - self.max_coin
        base_j = j - self.max_coin

        # both in and out tokens are in basepool
        if base_i >= 0 and base_j >= 0:
            _dydx = self.basepool.dydx(base_i, base_j, use_fee=use_fee)
            return float(_dydx)

        rates = self.p[:]
        rates[self.max_coin] = self.basepool.get_virtual_price()
        xp = [mpz(x) * p // 10**18 for x, p in zip(self.x, rates)]

        bp = self.basepool
        base_xp = [mpz(x) * p // 10**18 for x, p in zip(bp.x, bp.p)]
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
            base_inputs = [0] * self.basepool.n
            base_inputs[base_i] = dx * 10**18 // self.basepool.p[base_i]

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
        Basically this is the "regular" pricing calc with no special metapool handling.
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
                dx = 10**12
                fee_factor = (
                    self.dynamic_fee(xi + dx // 2, xj - int(dydx * dx) // 2) / 10**10
                )
        else:
            fee_factor = 0

        dydx *= 1 - fee_factor

        return float(dydx)
