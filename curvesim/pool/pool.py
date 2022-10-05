import traceback
from itertools import combinations
from math import prod

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from gmpy2 import mpz
from scipy.optimize import least_squares, root_scalar


class Pool:

    """
    Python model of Curve pool math.
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
        r=None,
    ):
        """
        A: Amplification coefficient
        D: Total deposit size
        n: number of currencies; if list, assumes meta-pool
        p: precision
        tokens: # of tokens; if meta-pool, this sets # of basepool tokens
        fee: fee with 10**10 precision (default = .004%)
        fee_mul: fee multiplier for dynamic fee pools
        admin_fee: percentage of `fee` with 10**10 precision (default = 50%)
        r: initial redemption price for RAI-like pools
        """
        # FIXME: set admin_fee default back to 5 * 10**9
        # once sim code is updated.  Right now we use 0
        # to pass the CI tests.

        if isinstance(n, list):  # is metapool
            self.A = A[0]  # actually A * n ** (n - 1) because it's an invariant
            self.n = n[0]
            self.max_coin = self.n - 1
            if not isinstance(fee, list):
                fee = [fee] * n[0]
            if not isinstance(admin_fee, list):
                admin_fee = [admin_fee] * n[0]
            self.fee = fee[0]
            self.admin_fee = admin_fee[0]

            self.basepool = Pool(
                A[1],
                D[1],
                n[1],
                tokens=tokens[1],
                fee=fee[1],
                admin_fee=admin_fee[1],
                fee_mul=fee_mul[1],
            )

            if p:
                self.p = p
                self.basepool.p = p
            else:
                self.p = [10**18] * n[0]
                self.basepool.p = [10**18] * n[1]

            if r:
                self.p[0] = r
                self.r = True
            else:
                self.r = False

            if isinstance(D[0], list):
                self.x = D[0]
            else:
                rates = self.p[:]
                rates[self.max_coin] = self.basepool.get_virtual_price()
                self.x = [D[0] // n[0] * 10**18 // _p for _p in rates]

            self.ismeta = True
            self.n_total = n[0] + n[1] - 1
            self.tokens = tokens[0]
            self.fee_mul = fee_mul[0]
            self.collected_admin_fees = [0] * n[0]

        else:
            self.A = A  # actually A * n ** (n - 1) because it's an invariant
            self.n = n
            self.fee = fee

            if p:
                self.p = p
            else:
                self.p = [10**18] * n

            if isinstance(D, list):
                self.x = D
            else:
                self.x = [D // n * 10**18 // _p for _p in self.p]

            if tokens is None:
                self.tokens = self.D()
            else:
                self.tokens = tokens
            self.fee_mul = fee_mul
            self.admin_fee = admin_fee
            self.ismeta = False
            self.r = False
            self.n_total = self.n
            self.collected_admin_fees = [0] * self.n

    def xp(self):
        return [x * p // 10**18 for x, p in zip(self.x, self.p)]

    def D(self, xp=None):
        A = self.A
        xp = xp or self.xp()
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

    def get_D_mem(self, balances, A):
        xp = [x * p // 10**18 for x, p in zip(balances, self.p)]
        return self.get_D(xp, A)

    def get_y(self, i, j, x, xp):
        """
        Calculate x[j] if one makes x[i] = x

        Done by solving quadratic equation iteratively.
        x_1**2 + x1 * (sum' - (A*n**n - 1) * D / (A * n**n)) = D ** (n+1)/(n ** (2 * n) * prod' * A)
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
        Calculate x[j] if one makes x[i] = x

        Done by solving quadratic equation iteratively.
        x_1**2 + x1 * (sum' - (A*n**n - 1) * D / (A * n**n)) = D ** (n+1)/(n ** (2 * n) * prod' * A)
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
        if not self.ismeta:
            xp = self.xp()
            x = xp[i] + dx * self.p[i] // 10**18
            y = self.get_y(i, j, x, xp)
            dy = xp[j] - y - 1

            if self.fee_mul is None:
                fee = dy * self.fee // 10**10
            else:
                fee = (
                    dy
                    * self.dynamic_fee((xp[i] + x) // 2, (xp[j] + y) // 2)
                    // 10**10
                )

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

        # exchange_underlying
        rates = self.p[:]
        rates[self.max_coin] = self.basepool.get_virtual_price()

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
                self.x[i] += dx
            else:
                # i is from BasePool
                # At first, get the amount of pool tokens
                base_inputs = [0] * self.basepool.n
                base_inputs[base_i] = dx
                # Deposit and measure delta
                dx = self.basepool.add_liquidity(
                    base_inputs
                )  # dx is # of minted basepool LP tokens
                self.x[self.max_coin] += dx
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

            self.x[meta_j] -= dy

            # Withdraw from the base pool if needed
            if base_j >= 0:
                dy, dy_fee = self.basepool.remove_liquidity_one_coin(dy, base_j)

        else:
            # If both are from the base pool
            dy, dy_fee = self.basepool.exchange(base_i, base_j, dx)

        return dy, dy_fee

    def calc_withdraw_one_coin(self, token_amount, i, use_fee=True):
        # FIXME: need to update for metapool
        A = self.A
        xp = self.xp()
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

    def calc_token_amount(self, amounts, use_fee=False):
        """
        Fee logic is based on add_liquidity, which makes this more accurate than
        the `calc_token_amount` in the actual contract, which neglects fees.

        By default, it's assumed you want the contract behavior.
        """
        # FIXME: need to handle rates for metapool
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
        return self.D() * 10**18 // self.tokens

    def dynamic_fee(self, xpi, xpj):
        xps2 = xpi + xpj
        xps2 *= xps2  # Doing just ** 2 can overflow apparently
        return (self.fee_mul * self.fee) // (
            (self.fee_mul - 10**10) * 4 * xpi * xpj // xps2 + 10**10
        )

    def dydxfee(self, i, j):
        """
        Returns price with fee, (dy[j]-fee)/dx[i]) given some dx[i]

        For metapools, the indices are assumed to include base pool
        underlyer indices.
        """
        return self.dydx(i, j, use_fee=True)

    def dydx(self, i, j, use_fee=False):
        """
        Returns price, dy[j]/dx[i], given some dx[i]

        For metapools, the indices are assumed to include base pool
        underlyer indices.
        """
        if self.ismeta:  # fees already included
            # --------------------------------
            # -- Metapool pricing formula ----
            # --------------------------------
            # z: primary coin balance
            # w: basepool virtual balance
            # x_i: basepool coin balances
            #
            # dz/dx_i = dz/dw  * dw/dx_i = dz/dw * dD/dx_i = dz/dw * D'
            # where D refers to the basepool
            #
            # D' = -1 * ( A * n ** (n+1) * prod(x_k) + D ** (n+1) / x_i)
            #          / ( n ** n * prod(x_k) - A * n ** (n+1) * prod(x_k) - (n + 1) * D ** n
            rates = self.p[:]
            rates[self.max_coin] = self.basepool.get_virtual_price()
            xp = [mpz(x) * p // 10**18 for x, p in zip(self.x, rates)]

            # Use base_i or base_j if they are >= 0
            base_i = i - self.max_coin
            base_j = j - self.max_coin

            if base_i < 0 or base_j < 0:  # if i or j not in basepool
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
                    dx = 10**12
                    base_inputs = [0] * self.basepool.n
                    base_inputs[base_i] = dx

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

                    # Convert to real units
                    dy = (dy - dy_fee) * 10**18 // rates[meta_j]

                    _dydx = dy / dx

            else:
                # Both are from the base pool
                _dydx = self.basepool.dydx(base_i, base_j, use_fee=use_fee)

        else:
            _dydx = self._dydx(i, j, use_fee=use_fee)

        return float(_dydx)

    def _dydx(self, i, j, xp=None, use_fee=False):
        """
        Treats indices as applying to the "top-level" pool if a metapool.
        Basically this is the "regular" pricing calc with no special metapool handling.
        """
        xp = xp or [mpz(x) for x in self.xp()]

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

    def optarb(self, i, j, p):
        """
        Estimates trade to optimally arbitrage coin[i]
        for coin[j] given external price p (base: i, quote: j)
        p must be less than dy[j]/dx[i], including fees

        Returns:
        trade: format (i,j,dx)
        errors: price errors, (dy-fee)/dx - p, for each pair of coins after the trades
        res: output from numerical estimator

        """
        if self.ismeta:
            # Use base_i or base_j if they are >= 0
            base_i = i - self.max_coin
            base_j = j - self.max_coin
            meta_i = self.max_coin
            meta_j = self.max_coin
            if base_i < 0:
                meta_i = i
            if base_j < 0:
                meta_j = j

            if base_i < 0 or base_j < 0:
                rates = self.p[:]
                rates[self.max_coin] = self.basepool.get_virtual_price()
                xp = [x * p // 10**18 for x, p in zip(self.x, rates)]
                hi = self.get_y(meta_j, meta_i, int(xp[meta_j] * 0.01), xp) - xp[meta_i]
            else:
                base_xp = self.basepool.xp()
                hi = (
                    self.basepool.get_y(
                        base_j, base_i, int(base_xp[base_j] * 0.01), base_xp
                    )
                    - base_xp[base_i]
                )

            bounds = (1, hi)

        else:
            xp = self.xp()
            bounds = (
                1,
                self.get_y(j, i, int(xp[j] * 0.01), xp) - xp[i],
            )  # Lo: 1, Hi: enough coin[i] to leave 1% of coin[j]

        res = root_scalar(
            arberror, args=(self, i, j, p), bracket=bounds, method="brentq"
        )

        trade = (i, j, int(res.root))

        error = arberror(res.root, self, i, j, p)

        return trade, error, res

    def optarbs(self, prices, limits):  # noqa: C901
        """
        Estimates trades to optimally arbitrage all coins
        in a pool, given prices and volume limits

        Returns:
        trades: list of trades with format (i,j,dx)
        error: (dy-fee)/dx - p
        res: output from numerical estimator

        """
        combos = list(combinations(range(self.n_total), 2))

        # Initial guesses for dx, limits, and trades
        # uses optarb (i.e., only considering price of coin[i] and coin[j])
        # guess will be too high but in range
        x0 = []
        lo = []
        hi = []
        coins = []
        price_targs = []
        for k, pair in enumerate(combos):
            i = pair[0]
            j = pair[1]
            if self.dydxfee(i, j) - prices[k] > 0:
                try:
                    trade, error, res = self.optarb(i, j, prices[k])
                    x0.append(min(trade[2], int(limits[k] * 10**18)))
                except Exception:
                    x0.append(0)

                lo.append(0)
                hi.append(int(limits[k] * 10**18) + 1)
                coins.append((i, j))
                price_targs.append(prices[k])

            elif self.dydxfee(j, i) - 1 / prices[k] > 0:
                try:
                    trade, error, res = self.optarb(j, i, 1 / prices[k])
                    x0.append(min(trade[2], int(limits[k] * 10**18)))
                except Exception:
                    x0.append(0)

                lo.append(0)
                hi.append(int(limits[k] * 10**18) + 1)
                coins.append((j, i))
                price_targs.append(1 / prices[k])

            else:
                x0.append(0)
                lo.append(0)
                hi.append(int(limits[k] * 10**18 + 1))
                coins.append((i, j))
                price_targs.append(prices[k])

        # Order trades in terms of expected size
        order = sorted(range(len(x0)), reverse=True, key=x0.__getitem__)
        x0 = [x0[i] for i in order]
        lo = [lo[i] for i in order]
        hi = [hi[i] for i in order]
        coins = [coins[i] for i in order]
        price_targs = [price_targs[i] for i in order]

        # Find trades that minimize difference between pool price and external market price
        trades = []
        try:
            res = least_squares(
                arberrors,
                x0=x0,
                args=(self, price_targs, coins),
                bounds=(lo, hi),
                gtol=10**-15,
                xtol=10**-15,
            )

            # Format trades into tuples, ignore if dx=0
            dxs = res.x

            for k in range(len(dxs)):
                if np.isnan(dxs[k]):
                    dx = 0
                else:
                    dx = int(dxs[k])

                if dx > 0:
                    i = coins[k][0]
                    j = coins[k][1]
                    trades.append((i, j, dx))

            errors = res.fun

        except Exception:
            print(traceback.format_exc())
            print(
                "Optarbs args:\n"
                + "x0: "
                + str(x0)
                + ", lo: "
                + str(lo)
                + ", hi: "
                + str(hi)
                + ", prices: "
                + str(price_targs),
                end="\n" * 2,
            )

            errors = np.array(arberrors([0] * len(x0), self, price_targs, coins))
            res = []
        return trades, errors, res

    def pricedepth(self, size=0.001):
        """
        Estimates proportion of pool holdings needed to move price by "size"; default = .1%

        """
        combos = list(combinations(range(self.n), 2))
        if self.ismeta:
            ismeta = True
            self.ismeta = (
                False  # pretend a normal pool to exchange for basepool LP token
            )
            p_before = self.p[:]
            self.p[
                self.max_coin
            ] = (
                self.basepool.get_virtual_price()
            )  # use virtual price for LP token precision
        else:
            ismeta = False

        sumxp = sum(self.xp())

        depth = []
        for i, j in combos:
            trade, _, _ = self.optarb(i, j, self.dydxfee(i, j) * (1 - size))
            depth.append(trade[2] / sumxp)

            trade, _, _ = self.optarb(j, i, self.dydxfee(j, i) * (1 - size))
            depth.append(trade[2] / sumxp)

        if ismeta:
            self.p = p_before
            self.ismeta = True

        return depth

    def dotrades(self, trades):
        """
        Does trades formatted as the output of optarbs

        Returns list of trades done in format (i,j,dx[i],dy[j]) and total volume

        """

        if self.ismeta:
            p = self.p[0 : self.max_coin] + self.basepool.p[:]
        else:
            p = self.p[:]

        trades_done = []
        volume = 0
        for trade in trades:
            i = trade[0]
            j = trade[1]
            dx = trade[2]

            dy, dy_fee = self.exchange(i, j, dx)
            trades_done.append((i, j, dx, dy))

            if self.ismeta:
                if (
                    i < self.max_coin or j < self.max_coin
                ):  # only count trades involving meta-asset
                    volume += dx * p[i] // 10**18  # in "DAI" units
            else:
                volume += dx * p[i] // 10**18  # in "DAI" units

        return trades_done, volume

    def orderbook(self, i, j, width=0.1, reso=10**23, show=True):  # noqa: C901

        # if j == 'b', get orderbook against basepool token
        p_mult = 1
        if j == "b":
            if i >= self.max_coin:
                raise ValueError("Coin i must be in the metapool for 'b' option")
            self.ismeta = (
                False  # pretend a normal pool to exchange for basepool LP token
            )
            p0 = self.p[:]
            self.p[
                self.max_coin
            ] = (
                self.basepool.get_virtual_price()
            )  # use virtual price for LP token precision
            j = 1
            metaRevert = True

            if self.r:
                p_mult = self.p[i]
        else:
            metaRevert = False

        # Store initial state
        x0 = self.x[:]
        if self.ismeta:
            x0_base = self.basepool.x[:]
            t0_base = self.basepool.tokens

        # Bids
        bids = [(self.dydx(i, j) * p_mult, 0)]  # tuples: price, depth
        size = 0

        while bids[-1][0] > bids[0][0] * (1 - width):
            size += reso
            self.exchange(i, j, size)
            price = self.dydx(i, j)
            bids.append((price * p_mult, size / 10**18))

            # Return to initial state
            self.x = x0[:]
            if self.ismeta:
                self.basepool.x = x0_base[:]
                self.basepool.tokens = t0_base

        # Asks
        asks = [(1 / self.dydx(j, i) * p_mult, 0)]  # tuples: price, depth
        size = 0

        while asks[-1][0] < asks[0][0] * (1 + width):
            size += reso
            dy, fee = self.exchange(j, i, size)
            price = 1 / self.dydx(j, i)
            asks.append((price * p_mult, dy / 10**18))

            # Return to initial state
            self.x = x0[:]
            if self.ismeta:
                self.basepool.x = x0_base[:]
                self.basepool.tokens = t0_base

        # Format DataFrames
        bids = pd.DataFrame(bids, columns=["price", "depth"]).set_index("price")
        asks = pd.DataFrame(asks, columns=["price", "depth"]).set_index("price")

        if metaRevert:
            self.p[:] = p0[:]
            self.ismeta = True

        if show:
            plt.plot(bids, color="red")
            plt.plot(asks, color="green")
            plt.xlabel("Price")
            plt.ylabel("Depth")
            plt.show()
        return bids, asks

    def bcurve(self, xs=None, show=True):
        if self.ismeta:
            combos = [(0, 1)]
            labels = ["Metapool Token", "Basepool LP Token"]

        else:
            combos = list(combinations(range(self.n), 2))
            labels = list(range(self.n))
            labels = ["Coin %s" % str(label) for label in labels]

        plt_n = 0
        xs_out = []
        ys_out = []
        for combo in combos:
            i = combo[0]
            j = combo[1]

            xp = self.xp()

            if xs is None:
                xs_i = np.linspace(
                    int(self.D() * 0.0001),
                    self.get_y(j, i, int(self.D() * 0.0001), xp),
                    1000,
                ).round()
            else:
                xs_i = xs

            ys_i = []
            for x in xs_i:
                ys_i.append(self.get_y(i, j, int(x)) / 10**18, xp)

            xs_i = xs_i / 10**18
            xs_out.append(xs_i)
            ys_out.append(ys_i)

            if show:
                if plt_n == 0:
                    fig, axs = plt.subplots(1, len(combos), constrained_layout=True)

                if len(combos) == 1:
                    ax = axs
                else:
                    ax = axs[plt_n]

                ax.plot(xs_i, ys_i, color="black")
                ax.scatter(xp[i] / 10**18, xp[j] / 10**18, s=40, color="black")
                ax.set_xlabel(labels[i])
                ax.set_ylabel(labels[j])
                plt_n += 1

        if show:
            plt.show()

        return xs_out, ys_out


# Error functions for optarb and optarbs
def arberror(dx, pool, i, j, p):
    if pool.ismeta and i >= pool.max_coin:
        base_i = i - pool.max_coin
        rate = pool.basepool.p[base_i]
    else:
        rate = pool.p[i]
    dx = int(dx) * 10**18 // rate

    x_old = pool.x[:]
    if pool.ismeta:
        x_old_base = pool.basepool.x[:]
        tokens_old = pool.basepool.tokens

    pool.exchange(i, j, dx)  # do trade

    # Check price error after trade
    # Error = pool price (dy/dx) - external price (p);
    error = pool.dydxfee(i, j) - p

    pool.x = x_old
    if pool.ismeta:
        pool.basepool.x = x_old_base
        pool.basepool.tokens = tokens_old

    return error


def arberrors(dxs, pool, price_targs, coins):
    rates = pool.p[:]
    x_old = pool.x[:]

    if pool.ismeta:
        x_old_base = pool.basepool.x[:]
        tokens_old = pool.basepool.tokens
        rates.pop()
        rates.extend(pool.basepool.p)

    # Do each trade
    for k, pair in enumerate(coins):
        i = pair[0]
        j = pair[1]

        if np.isnan(dxs[k]):
            dx = 0
        else:
            dx = int(dxs[k]) * 10**18 // rates[i]

        if dx > 0:
            pool.exchange(i, j, dx)

    # Check price errors after all trades
    errors = []
    for k, pair in enumerate(coins):
        i = pair[0]
        j = pair[1]
        p = price_targs[k]
        errors.append(pool.dydxfee(i, j) - p)

    pool.x = x_old
    if pool.ismeta:
        pool.basepool.x = x_old_base
        pool.basepool.tokens = tokens_old

    return errors
