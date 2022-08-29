import os
from ast import literal_eval
from datetime import datetime, timedelta
from functools import partial
from itertools import combinations, product
from math import factorial, prod
from multiprocessing import Pool

from gmpy2 import mpz
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import requests
from matplotlib.lines import Line2D
from scipy.optimize import least_squares, root_scalar
from web3 import Web3

import coingecko
import nomics


class pool:

    """
    Python model of Curve pool math.
    """

    def __init__(self, A, D, n, p=None, tokens=None, fee=4 * 10**6, feemul=None, r=None):
        """
        A: Amplification coefficient
        D: Total deposit size
        n: number of currencies; if list, assumes meta-pool
        p: precision
        tokens: # of tokens; if meta-pool, this sets # of basepool tokens
        fee: fee with 10**10 precision (default = .004%)
        feemul: fee multiplier for dynamic fee pools
        r: initial redemption price for RAI-like pools
        """

        if isinstance(n, list):  # is metapool
            self.A = A[0]  # actually A * n ** (n - 1) because it's an invariant
            self.n = n[0]
            self.max_coin = self.n - 1
            if not isinstance(fee, list):
                fee = [fee] * n[0]
            self.fee = fee[0]

            self.basepool = pool(A[1], D[1], n[1], fee=fee[1], tokens=tokens)

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
            self.tokens = self.D()
            self.feemul = feemul

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
            self.feemul = feemul
            self.ismeta = False
            self.r = False
            self.n_total = self.n

    def xp(self):
        return [x * p // 10**18 for x, p in zip(self.x, self.p)]

    def D(self, xp=None):
        """
        D invariant calculation in non-overflowing integer operations
        iteratively

        A * sum(x_i) * n**n + D = A * D * n**n + D**(n+1) / (n**n * prod(x_i))

        Converging solution:
        D[j+1] = (A * n**n * sum(x_i) - D[j]**(n+1) / (n**n prod(x_i))) / (A * n**n - 1)
        """
        Dprev = 0
        if xp is None:
            xp = self.xp()
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

    def y(self, i, j, x, xp=None):
        """
        Calculate x[j] if one makes x[i] = x

        Done by solving quadratic equation iteratively.
        x_1**2 + x1 * (sum' - (A*n**n - 1) * D / (A * n**n)) = D ** (n+1)/(n ** (2 * n) * prod' * A)
        x_1**2 + b*x_1 = c

        x_1 = (x_1**2 + c) / (2*x_1 + b)
        """

        if xp is None:
            xx = self.xp()
        else:
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
        return y  # the result is in underlying units too

    def y_underlying(self, i, j, x):
        # For meta-pool
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

            if base_i >= 0:
                # i is from BasePool
                # At first, get the amount of pool tokens
                dx = x - self.basepool.xp()[base_i]
                base_inputs = [0] * self.basepool.n
                base_inputs[base_i] = dx

                dx = self.basepool.calc_token_amount(base_inputs)
                # Need to convert pool token to "virtual" units using rates
                x = dx * rates[self.max_coin] // 10**18
                # Adding number of pool tokens
                x += xp[self.max_coin]

            y = self.y(meta_i, meta_j, x, xp)

            if base_j >= 0:
                dy = xp[meta_j] - y - 1
                dy_fee = dy * self.fee // 10**10

                # Convert all to real units
                # Works for both pool coins and real coins
                dy = (dy - dy_fee) * 10**18 // rates[meta_j]

                D0 = self.basepool.D()
                D1 = D0 - dy * D0 // self.basepool.tokens
                y = self.y_D(base_j, D1)

        else:
            # If both are from the base pool
            y = self.basepool.y(base_i, base_j, x)

        return y

    def y_D(self, i, _D):
        """
        Calculate x[j] if one makes x[i] = x

        Done by solving quadratic equation iteratively.
        x_1**2 + x1 * (sum' - (A*n**n - 1) * D / (A * n**n)) = D ** (n+1)/(n ** (2 * n) * prod' * A)
        x_1**2 + b*x_1 = c

        x_1 = (x_1**2 + c) / (2*x_1 + b)
        """
        xx = self.xp()
        xx = [xx[k] for k in range(self.n) if k != i]
        S = sum(xx)
        Ann = self.A * self.n
        c = _D
        for y in xx:
            c = c * _D // (y * self.n)
        c = c * _D // (self.n * Ann)
        b = S + _D // Ann
        y_prev = 0
        y = _D
        while abs(y - y_prev) > 1:
            y_prev = y
            y = (y**2 + c) // (2 * y + b - _D)
        return y  # the result is in underlying units too

    def dy(self, i, j, dx):
        if self.ismeta:  # note that fees are already included
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
                else:
                    # i is from BasePool
                    # At first, get the amount of pool tokens
                    base_inputs = [0] * self.basepool.n
                    base_inputs[base_i] = dx

                    dx = self.basepool.calc_token_amount(base_inputs)
                    # Need to convert pool token to "virtual" units using rates
                    x = dx * rates[self.max_coin] // 10**18
                    # Adding number of pool tokens
                    x += xp[self.max_coin]

                y = self.y(meta_i, meta_j, x, xp)

                # Either a real coin or token
                dy = xp[meta_j] - y - 1
                dy_fee = dy * self.fee // 10**10

                # Convert all to real units
                # Works for both pool coins and real coins
                dy = (dy - dy_fee) * 10**18 // rates[meta_j]

                if base_j >= 0:
                    dy = self.basepool.calc_withdraw_one_coin(dy, base_j)

            else:
                # If both are from the base pool
                dy = self.basepool.dy(base_i, base_j, dx)
                dy = dy - dy * self.fee // 10**10

            return dy

        else:  # if not meta-pool
            # dx and dy are in underlying units
            xp = self.xp()
            return xp[j] - self.y(i, j, xp[i] + dx)

    def exchange(self, i, j, dx):
        if self.ismeta:  # exchange_underlying
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
                    dx = self.basepool.add_liquidity(base_inputs)  # dx is # of minted basepool LP tokens
                    self.x[self.max_coin] += dx
                    # Need to convert pool token to "virtual" units using rates
                    x = dx * rates[self.max_coin] // 10**18
                    # Adding number of pool tokens
                    x += xp[self.max_coin]

                y = self.y(meta_i, meta_j, x, xp)

                # Either a real coin or token
                dy = xp[meta_j] - y - 1
                dy_fee = dy * self.fee // 10**10

                # Convert all to real units
                # Works for both pool coins and real coins
                dy_nofee = dy * 10**18 // rates[meta_j]
                dy = (dy - dy_fee) * 10**18 // rates[meta_j]

                self.x[meta_j] -= dy

                # Withdraw from the base pool if needed
                if base_j >= 0:
                    dy = self.basepool.remove_liquidity_one_coin(dy, base_j)
                    dy_nofee = self.basepool.calc_withdraw_one_coin(dy_nofee, base_j, fee=False)
                    dy_fee = dy_nofee - dy

            else:
                # If both are from the base pool
                dy, dy_fee = self.basepool.exchange(base_i, base_j, dx)

            return dy, dy_fee

        else:  # if not meta-pool, normal exchange
            xp = self.xp()
            x = xp[i] + dx
            y = self.y(i, j, x)
            dy = xp[j] - y
            if self.feemul is None:  # if not dynamic fee pool
                fee = dy * self.fee // 10**10
            else:  # if dynamic fee pool
                fee = dy * self.dynamic_fee((xp[i] + x) // 2, (xp[j] + y) // 2) // 10**10
            assert dy > 0
            self.x[i] = x * 10**18 // self.p[i]
            self.x[j] = (y + fee) * 10**18 // self.p[j]
            return dy - fee, fee

    def remove_liquidity_imbalance(self, amounts):
        _fee = self.fee * self.n // (4 * (self.n - 1))

        old_balances = self.x
        new_balances = self.x[:]
        D0 = self.D()
        for i in range(self.n):
            new_balances[i] -= amounts[i]
        self.x = new_balances
        D1 = self.D()
        self.x = old_balances
        fees = [0] * self.n
        for i in range(self.n):
            ideal_balance = D1 * old_balances[i] // D0
            difference = abs(ideal_balance - new_balances[i])
            fees[i] = _fee * difference // 10**10
            new_balances[i] -= fees[i]
        self.x = new_balances
        D2 = self.D()
        self.x = old_balances

        token_amount = (D0 - D2) * self.tokens // D0

        return token_amount

    def calc_withdraw_one_coin(self, token_amount, i, fee=True):
        xp = self.xp()
        if self.fee and fee:
            fee = self.fee - self.fee * xp[i] // sum(xp) + 5 * 10**5
        else:
            fee = 0

        D0 = self.D()
        D1 = D0 - token_amount * D0 // self.tokens
        dy = xp[i] - self.y_D(i, D1)

        return dy - dy * fee // 10**10

    def add_liquidity(self, amounts):
        _fee = self.fee * self.n // (4 * (self.n - 1))

        old_balances = self.x
        new_balances = self.x[:]
        D0 = self.D()

        for i in range(self.n):
            new_balances[i] += amounts[i]
        self.x = new_balances
        D1 = self.D()
        self.x = old_balances

        fees = [0] * self.n
        mint_balances = new_balances[:]
        for i in range(self.n):
            ideal_balance = D1 * old_balances[i] // D0
            difference = abs(ideal_balance - new_balances[i])
            fees[i] = _fee * difference // 10**10
            mint_balances[i] -= fees[i]  # used to calculate mint amount

        self.x = mint_balances
        D2 = self.D()
        self.x = new_balances

        mint_amount = self.tokens * (D2 - D0) // D0
        self.tokens += mint_amount

        return mint_amount

    def remove_liquidity_one_coin(self, token_amount, i):
        dy = self.calc_withdraw_one_coin(token_amount, i)
        self.x[i] -= dy
        self.tokens -= token_amount
        return dy

    def calc_token_amount(self, amounts):
        # Based on add_liquidity (more accurate than calc_token_amount in actual contract)
        _fee = self.fee * self.n // (4 * (self.n - 1))

        old_balances = self.x
        new_balances = self.x[:]
        D0 = self.D()

        for i in range(self.n):
            new_balances[i] += amounts[i]
        self.x = new_balances
        D1 = self.D()
        self.x = old_balances

        fees = [0] * self.n
        mint_balances = new_balances[:]
        for i in range(self.n):
            ideal_balance = D1 * old_balances[i] // D0
            difference = abs(ideal_balance - new_balances[i])
            fees[i] = _fee * difference // 10**10
            mint_balances[i] -= fees[i]  # used to calculate mint amount

        self.x = mint_balances
        D2 = self.D()
        self.x = old_balances

        mint_amount = self.tokens * (D2 - D0) // D0

        return mint_amount

    def get_virtual_price(self):
        return self.D() * 10**18 // self.tokens

    def dynamic_fee(self, xpi, xpj):
        xps2 = xpi + xpj
        xps2 *= xps2  # Doing just ** 2 can overflow apparently
        return (self.feemul * self.fee) // ((self.feemul - 10**10) * 4 * xpi * xpj // xps2 + 10**10)

    def dydx(self, i, j, dx):
        """
        Returns price, dy[j]/dx[i], given some dx[i]
        """
        dy = self.dy(i, j, dx)
        return dy / dx

    def old_dydxfee(self, i, j, dx):
        """
        For testing only.  This is the old calc.

        Returns price with fee, (dy[j]-fee)/dx[i]) given some dx[i]
        """
        if self.ismeta:  # fees already included
            dy = self.dy(i, j, dx)
        else:
            if self.feemul is None:  # if not dynamic fee pool
                dy = self.dy(i, j, dx)
                fee = dy * self.fee // 10**10
            else:  # if dynamic fee pool
                xp = self.xp()
                x = xp[i] + dx
                y = self.y(i, j, x)
                dy = xp[j] - y
                fee = dy * self.dynamic_fee((xp[i] + x) // 2, (xp[j] + y) // 2) // 10**10

            dy = dy - fee
        return dy / dx

    def dydxfee(self, i, j, dx):
        """
        Returns price with fee, (dy[j]-fee)/dx[i]) given some dx[i]

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
                    D_prime = -1 * (A_pow * x_prod + D_pow / xj) / (n ** n * x_prod - A_pow * x_prod - (n+1) * D ** n)
                    D_prime = float(D_prime)

                    dwdz = self._dydxfee(0, self.max_coin, xp)
                    new_dydxfee = dwdz / D_prime

                    if bp.fee:
                        fee = bp.fee - bp.fee * xj // sum(base_xp) + 5 * 10**5
                    else:
                        fee = 0
                    new_dydxfee *= (1 - fee / 10 ** 10)

                    # old_dydxfee = self.old_dydxfee(i, j, dx)
                    # diff = abs(old_dydxfee - new_dydxfee)
                    # if diff > 4e-12:
                    #     print("meta - primary to base")
                    #     print("Old dydx fee:", old_dydxfee)
                    #     print("New dydx fee:", new_dydxfee)
                    #     print("Difference:", diff)
                    #     print("    D':", D_prime)
                    #     print("    dwdz:", dwdz)
                    #     print("    fee factor:", (1 - fee / 10 ** 10))
                    #     print("-------------")

                else:  # i is from basepool
                    base_inputs = [0] * self.basepool.n
                    base_inputs[base_i] = dx

                    dw = self.basepool.calc_token_amount(base_inputs)
                    # Convert lp token amount to virtual units
                    dw = dw * rates[self.max_coin] // 10**18
                    x = xp[self.max_coin] + dw

                    meta_i = self.max_coin
                    meta_j = j
                    y = self.y(meta_i, meta_j, x, xp)

                    dy = xp[meta_j] - y - 1
                    dy_fee = dy * self.fee // 10**10

                    # Convert to real units
                    dy = (dy - dy_fee) * 10**18 // rates[meta_j]

                    new_dydxfee = dy / dx

                    # old_dydxfee = self.old_dydxfee(i, j, dx)
                    # diff = abs(old_dydxfee - new_dydxfee)
                    # if diff > 4e-12:
                    #     print("meta - base to primary")
                    #     print("Old dydx fee:", old_dydxfee)
                    #     print("New dydx fee:", new_dydxfee)
                    #     print("Difference:", diff)
                    #     print("-------------")

            else:
                # Both are from the base pool
                new_dydxfee = self.basepool.dydxfee(base_i, base_j, dx)

        else:
            new_dydxfee = self._dydxfee(i, j)

        return float(new_dydxfee)

    def _dydxfee(self, i, j, xp=None):
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
        dydx = (xj * (xi * A_pow * x_prod + D_pow)) / (xi * (xj * A_pow * x_prod + D_pow))

        if self.feemul is None:
            fee_factor = self.fee / 10**10
        else:
            dx = 10 ** 12
            fee_factor = self.dynamic_fee(xi + dx // 2, xj - int(dydx * dx) // 2) / 10**10

        new_dydxfee = dydx * (1 - fee_factor)
        new_dydxfee = float(new_dydxfee)

        # dx = 10 ** 12
        # y = self.y(i, j, xi + dx, xp=xp)
        # dy = xj - y 
        # if self.feemul:
        #     x = xi + dx
        #     fee = dy * self.dynamic_fee((xi + x) // 2, (xj + y) // 2) // 10**10
        # else:
        #     fee = dy * self.fee // 10**10
        # old_dydxfee = (dy - fee) / dx
        # diff = abs(old_dydxfee - new_dydxfee)
        # if diff > 3e-12:
        #     print("Old dydx fee:", old_dydxfee)
        #     print("New dydx fee:", new_dydxfee)
        #     print("Difference:", diff)
        #     print("Old dydx:", dy / dx)
        #     print("New dydx:", dydx)
        #     print("Difference:", abs(dydx - dy/dx))
        #     print("------------")
        return new_dydxfee

    def optarb(self, i, j, p):
        """
        Estimates trade to optimally arbitrage coin[i] for coin[j] given external price p (base: i, quote: j)
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

                hi = self.y(meta_j, meta_i, int(xp[meta_j] * 0.01), xp) - self.xp()[meta_i]
            else:
                hi = (
                    self.basepool.y(base_j, base_i, int(self.basepool.xp()[base_j] * 0.01))
                    - self.basepool.xp()[base_i]
                )

            bounds = (10**12, hi)

        else:
            bounds = (
                10**12,
                self.y(j, i, int(self.xp()[j] * 0.01)) - self.xp()[i],
            )  # Lo: 1, Hi: enough coin[i] to leave 1% of coin[j]

        res = root_scalar(arberror, args=(self, i, j, p), bracket=bounds, method="brentq")

        trade = (i, j, int(res.root))

        error = arberror(res.root, self, i, j, p)

        return trade, error, res

    def optarbs(self, prices, limits):  # noqa: C901
        """
        Estimates trades to optimally arbitrage all coins in a pool, given prices and volume limits

        Returns:
        trades: list of trades with format (i,j,dx)
        error: (dy-fee)/dx - p
        res: output from numerical estimator

        """
        combos = list(combinations(range(self.n_total), 2))

        # Initial guesses for dx, limits, and trades
        # uses optarb (i.e., only considering price of coin[i] and coin[j])
        # guess will be too high but in range
        k = 0
        x0 = []
        lo = []
        hi = []
        coins = []
        price_targs = []
        for pair in combos:
            i = pair[0]
            j = pair[1]
            if arberror(10**12, self, i, j, prices[k]) > 0:
                try:
                    trade, error, res = self.optarb(i, j, prices[k])
                    x0.append(min(trade[2], int(limits[k] * 10**18)))
                except Exception:
                    x0.append(0)

                lo.append(0)
                hi.append(int(limits[k] * 10**18) + 1)
                coins.append((i, j))
                price_targs.append(prices[k])

            elif arberror(10**12, self, j, i, 1 / prices[k]) > 0:
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
            k += 1

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
            print(
                "[Error: Optarbs] x0: "
                + str(x0)
                + " lo: "
                + str(lo)
                + " hi: "
                + str(hi)
                + " prices: "
                + str(price_targs)
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
            self.ismeta = False  # pretend a normal pool to exchange for basepool LP token
            p_before = self.p[:]
            self.p[
                self.max_coin
            ] = self.basepool.get_virtual_price()  # use virtual price for LP token precision
        else:
            ismeta = False

        sumxp = sum(self.xp())

        depth = []
        for i, j in combos:
            trade, error, res = self.optarb(i, j, self.dydxfee(i, j, 10**12) * (1 - size))
            depth.append(trade[2] / sumxp)

            trade, error, res = self.optarb(j, i, self.dydxfee(j, i, 10**12) * (1 - size))
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
                if i < self.max_coin or j < self.max_coin:  # only count trades involving meta-asset
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
            self.ismeta = False  # pretend a normal pool to exchange for basepool LP token
            p0 = self.p[:]
            self.p[
                self.max_coin
            ] = self.basepool.get_virtual_price()  # use virtual price for LP token precision
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
        bids = [(self.dydx(i, j, 10**12) * p_mult, 10**12 / 10**18)]  # tuples: price, depth
        size = 0

        while bids[-1][0] > bids[0][0] * (1 - width):
            size += reso
            self.exchange(i, j, size)
            price = self.dydx(i, j, 10**12)
            bids.append((price * p_mult, size / 10**18))

            # Return to initial state
            self.x = x0[:]
            if self.ismeta:
                self.basepool.x = x0_base[:]
                self.basepool.tokens = t0_base

        # Asks
        asks = [(1 / self.dydx(j, i, 10**12) * p_mult, 10**12 / 10**18)]  # tuples: price, depth
        size = 0

        while asks[-1][0] < asks[0][0] * (1 + width):
            size += reso
            dy, fee = self.exchange(j, i, size)
            price = 1 / self.dydx(j, i, 10**12)
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

            if xs is None:
                xs_i = np.linspace(int(self.D() * 0.0001), self.y(j, i, int(self.D() * 0.0001)), 1000).round()
            else:
                xs_i = xs

            ys_i = []
            for x in xs_i:
                ys_i.append(self.y(i, j, int(x)) / 10**18)

            xs_i = xs_i / 10**18
            xs_out.append(xs_i)
            ys_out.append(ys_i)

            xp = self.xp()[:]

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


# Simulation functions
def sim(A, D, n, fee, prices, volumes, tokens=None, feemul=None, vol_mult=1, r=None):
    """
    Simulates a pool with parameters A, D, n, and fee, given time series of prices and volumes

    A: amplitude parameter, technically A*n**(n - 1), as in the pool contracts
    D: Total deposit size, precision 10**18
    n: number of currencies; if list, assumes meta-pool
    fee: fee with precision 10**10. Default fee is .0004 (.04%)
    prices: time series of pairwise prices
    volumes: time series of pairwise exchange volumes

    tokens: # of tokens; if meta-pool, this sets # of basepool tokens
    feemul: fee multiplier for dynamic fee pools
    vol_mult: scalar or vector (one element per pair) multiplied by market volume to limit trade sizes
    r: time series of redemption prices for RAI-like pools

    Returns:
    pl: pool object at end of simulation
    err: time series of absolute price errors, (dy-fee)/dx - p, summed accros coin pairs
    bal: balance parameter over time; bal=1 when in perfect balance, and bal=0 when all holdings are in 1 coin
    pool_value: time series of pool's value (based on virtual price)
    depth: time series of price depth, averaged across pool's coin; see pricedepth()
    volume: time series of pool volume
    xs: time series of pool holdings
    ps: time series of pool precisions (incl. basepool virtual price and/or RAI redemption price)

    """

    print("Simulating A=" + str(A) + ", Fee=" + str(np.array(fee) / int(10**8)) + "%")

    if r is not None:
        r = r.reindex(prices.index, method="ffill")
        r0 = int(r.price[0])
    else:
        r0 = None

    # Initiate pool
    pl = pool(A, D, n, fee=fee, tokens=tokens, feemul=feemul, r=r0)

    # Loop through timepoints and do optimal arb trades
    err = []
    bal = []
    pool_value = []
    depth = []
    volume = []
    xs = []
    ps = []

    for t in range(len(prices)):
        curr_prices = prices.iloc[t]
        curr_volume = volumes.iloc[t] * vol_mult
        if r is not None:
            pl.p[0] = int(r.price[t])  # update redemption price if needed

        trades, errors, res = pl.optarbs(curr_prices, curr_volume)
        if len(trades) > 0:
            trades_done, trade_volume = pl.dotrades(trades)
            volume.append(trade_volume / 10**18)
        else:
            volume.append(0)

        err.append(sum(abs(errors)))
        depth.append(np.sum(pl.pricedepth()) / 2)

        if pl.ismeta:
            # Pool Value
            rates = pl.p[:]
            rates[pl.max_coin] = pl.basepool.get_virtual_price()
            if r0 is not None:
                rates[pl.max_coin - 1] = r0  # value pool with redemption price held constant
            xp = [x * p // 10**18 for x, p in zip(pl.x, rates)]
            pool_value.append(pl.D(xp=xp))

            # Balance
            if r0 is not None:
                rates[pl.max_coin - 1] = int(r.price[t])  # compute balance with current redemption price
                xp = [x * p // 10**18 for x, p in zip(pl.x, rates)]
            xp = np.array(xp)
            bal.append(1 - sum(abs(xp / sum(xp) - 1 / n[0])) / (2 * (n[0] - 1) / n[0]))
            ps.append(rates)
        else:
            xp = np.array(pl.xp())
            pool_value.append(pl.D())
            bal.append(1 - sum(abs(xp / sum(xp) - 1 / n)) / (2 * (n - 1) / n))
            ps.append(pl.p[:])

        xs.append(pl.x[:])

    pool_value = np.array(pool_value).astype(float) / 10**18
    return pl, err, bal, pool_value, depth, volume, xs, ps


def psim(
    A_list,
    D,
    n,
    fee_list,
    prices,
    volumes,
    A_base=None,
    fee_base=None,
    tokens=None,
    feemul=None,
    vol_mult=1,
    r=None,
    plot=False,
    ncpu=4,
):
    """
    Calls sim() with a variety of A parameters (A_list) and/or fees (fee_list)
    Parallelized using multiprocessing starmap()

    A_list: list of A values
    D: Total deposit size, precision 10**18
    n: number of currencies; if list, assumes meta-pool
    fee_list: list of fees with precision 10**10
    prices: time series of pairwise prices
    volumes: time series of pairwise exchange volumes

    A_base: if metapool, A parameter for basepool
    fee_base: if metapool, fee for basepool
    tokens: # of tokens; if meta-pool, this sets # of basepool tokens
    feemul: fee multiplier for dynamic fee pools
    vol_mult: scalar or vector (one element per pair) multiplied by market volume to limit trade sizes
    r: time series of redemption prices for RAI-like pools
    plot: if true, plots outputs
    ncpu: number of CPUs to use for parallel processing


    Returns a dict containing:
    ar: annualized returns
    bal: balance parameter over time; bal=1 when in perfect balance, and bal=0 when all holdings are in 1 coin
    pool_value: time series of pool's value (based on virtual price)
    depth: time series of price depth, averaged across pool's coin; see pricedepth()
    volume: time series of pool volume
    log_returns: log returns over time
    err: time series of absolute price errors, (dy-fee)/dx - p, summed accros coin pairs
    x: time series of pool holdings
    p: time series of pool precisions (incl. basepool virtual price and/or RAI redemption price)

    """

    # Format inputs
    A_list = [int(round(A)) for A in A_list]
    fee_list = [int(round(fee)) for fee in fee_list]
    A_list_orig = A_list
    fee_list_orig = fee_list

    p_list = list(product(A_list, fee_list))

    if A_base is not None:
        A_list = [[A, A_base] for A in A_list]

    if fee_base is not None:
        fee_list = [[fee, fee_base] for fee in fee_list]

    # Run sims
    simmapfunc = partial(sim, tokens=tokens, feemul=feemul, vol_mult=vol_mult, r=r)
    if ncpu > 1:
        with Pool(ncpu) as clust:
            pl, err, bal, pool_value, depth, volume, xs, ps = zip(
                *clust.starmap(
                    simmapfunc,
                    [(A, D, n, fee, prices, volumes) for A in A_list for fee in fee_list],
                )
            )
    else:
        params_list = zip(*[(A, D, n, fee, prices, volumes) for A in A_list for fee in fee_list])
        pl, err, bal, pool_value, depth, volume, xs, ps = zip(*map(simmapfunc, *params_list))

    # Output as DataFrames
    p_list = pd.MultiIndex.from_tuples(p_list, names=["A", "fee"])

    err = pd.DataFrame(err, index=p_list, columns=prices.index)
    bal = pd.DataFrame(bal, index=p_list, columns=prices.index)
    pool_value = pd.DataFrame(pool_value, index=p_list, columns=prices.index)
    depth = pd.DataFrame(depth, index=p_list, columns=prices.index)
    volume = pd.DataFrame(volume, index=p_list, columns=prices.index)

    log_returns = pd.DataFrame(np.log(pool_value).diff(axis=1).iloc[:, 1:])

    try:
        freq = prices.index.freq / timedelta(minutes=1)
    except Exception:
        freq = 30
    yearmult = 60 / freq * 24 * 365
    ar = pd.DataFrame(np.exp(log_returns.mean(axis=1) * yearmult) - 1)

    x = pd.DataFrame(xs, index=p_list, columns=prices.index)
    p = pd.DataFrame(ps, index=p_list, columns=prices.index)

    # Plotting
    if plot:
        if len(fee_list) > 1:
            plotsimsfee(A_list_orig, fee_list_orig, ar, bal, depth, volume, err)
        else:
            plotsims(A_list_orig, ar, bal, pool_value, depth, volume, log_returns, err)

    res = {
        "ar": ar,
        "bal": bal,
        "pool_value": pool_value,
        "depth": depth,
        "volume": volume,
        "log_returns": log_returns,
        "err": err,
        "x": x,
        "p": p,
    }

    return res


def autosim(  # noqa: C901
    poolname,
    test=False,
    A=None,
    D=None,
    fee=None,
    vol_mult=None,
    vol_mode=1,
    feemul=None,
    src="cg",
    ncpu=4,
    trunc=None,
):
    """
    Simplified function to simulate existing Curve pools.
    Fetches pool state and 2-months price data, runs psim, and saves results images to "pools" directory.

    Requires an entry for "poolname" in poolDF.csv

    A, D, fee, vol_mult, & feemul can be used to override default values and/or fetched data.
    D & fee should be provided in "natural" units (i.e., not 10**18 or 10**10 precision).
    A & fee must be lists/np.arrays.

    If test==True, uses a limited number of A/fee values

    vol_mode: chooses method for estimating vol_mult (i.e., trade volume limiter)
        -1: limits trade volumes proportionally to market volume for each pair
        -2: limits trade volumes equally across pairs
        -3: mode 2 for trades with meta-pool asset, mode 1 for basepool-only trades

    src: chooses data source
        -'cg': CoinGecko (free)
        -'nomics': nomics (requires paid API key in nomics.py)
        -'local': pulls from CSVs in "data" folder

    ncpu: number of CPUs to use for parallel processing
    trunc: truncate price/volume data to [trunc[0]:trunc[1]]

    Returns results dict from psim
    """

    # Get current pool data
    print("[" + poolname + "] Fetching pool data...")
    if src == "cg":
        csv = "poolDF_cg.csv"
    else:
        csv = "poolDF_nomics.csv"

    pldata = pooldata(poolname, csv=csv, balanced=True)

    histvolume = pldata["histvolume"]
    coins = pldata["coins"]
    n = pldata["n"]

    # Over-ride D & feemul if necessary
    if D is None:
        D = pldata["D"]
    else:
        D = int(D * 10**18)
        if isinstance(pldata["D"], list):  # if metapool
            pldata["D"][0] = D
            D = pldata["D"]

    if feemul is None:
        feemul = pldata["feemul"]

    # Update and load price data
    if src == "nomics":
        print("[" + poolname + "] Fetching Nomics price data...")
        # update CSVs
        t_end = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        t_start = t_end - timedelta(days=60)
        print("Timerange: %s to %s" % (str(t_start), str(t_end)))
        nomics.update(coins, None, t_start, t_end)

        # Load data
        prices, volumes, pzero = nomics.poolprices(coins)

    elif src == "local":
        print("[" + poolname + "] Fetching local price data...")
        prices, volumes, pzero = nomics.poolprices(coins)

    elif src == "cg":
        print("[" + poolname + "] Fetching CoinGecko price data...")
        prices, volumes = coingecko.poolprices(coins, "usd", 60)

    # Truncate data if needed
    if trunc is not None:
        prices = prices[trunc[0] : trunc[1]]
        volumes = volumes[trunc[0] : trunc[1]]

    # Calculate volume multiplier
    if vol_mult is None:
        if isinstance(n, list):  # is metapool
            n_base_pairs = int(factorial(n[1]) / 2 * factorial(n[1] - 2))
            if vol_mode == 1:
                vol_mult = histvolume[0] / volumes.sum()[0 : n[1]].sum().repeat(
                    n[1]
                )  # trades including meta-pool coin
                vol_mult = np.append(
                    vol_mult, histvolume[1] / volumes.sum()[n[1] :].sum().repeat(n_base_pairs)
                )  # basepool trades
            elif vol_mode == 2:
                vol_mult = histvolume[0].repeat(n[1]) / n[1] / volumes.sum()[0 : n[1]]
                vol_mult = np.append(
                    vol_mult, histvolume[1].repeat(n_base_pairs) / n_base_pairs / volumes.sum()[n[1] :]
                )
            elif vol_mode == 3:
                vol_mult = histvolume[0].repeat(n[1]) / n[1] / volumes.sum()[0 : n[1]]
                vol_mult = np.append(
                    vol_mult, histvolume[1] / volumes.sum()[n[1] :].sum().repeat(n_base_pairs)
                )

        else:
            if vol_mode == 1:
                vol_mult = histvolume / volumes.sum().sum()
            if vol_mode == 2:
                vol_mult = histvolume.repeat(n) / n / volumes.sum()
            if vol_mode == 3:
                print("Vol_mode=3 only available for meta-pools. Reverting to vol_mode=1")
                vol_mult = histvolume / volumes.sum().sum()
    print("Volume multipliers:")
    print(vol_mult)

    # Default ranges of A and fee values
    if A is None:
        A_list = 2 ** (np.array(range(12, 28)) / 2)
    else:
        A_list = np.array(A)

    if fee is None:
        fee_list = np.linspace(0.0002, 0.0006, 5) * 10**10
    else:
        fee_list = np.array(fee) * 10**10

    # Test values
    if test:
        A_list = np.array([100, 1000])
        fee_list = np.array([0.0003, 0.0004]) * 10**10

    # Run sims
    A_list = [int(round(A)) for A in A_list]
    fee_list = [int(round(fee)) for fee in fee_list]

    res = psim(
        A_list,
        D,
        n,
        fee_list,
        prices,
        volumes,
        A_base=pldata["A_base"],
        fee_base=pldata["fee_base"],
        tokens=pldata["tokens"],
        feemul=feemul,
        vol_mult=vol_mult,
        r=pldata["r"],
        plot=False,
        ncpu=ncpu,
    )

    # Save plots
    saveplots(
        poolname,
        A_list,
        fee_list,
        res["ar"],
        res["bal"],
        res["depth"],
        res["volume"],
        res["pool_value"],
        res["log_returns"],
        res["err"],
    )

    # Save text
    combos = list(combinations(coins, 2))
    startstr = prices.index[0].strftime("%m/%d/%y")
    endstr = prices.index[-1].strftime("%m/%d/%y")
    txt = "Simulation period: " + startstr + " to " + endstr

    if src == "cg":
        ps = "CAUTION: Trade volume limiting may be less accurate for CoinGecko data."
    else:
        ps = "Data Availability:\n"
        for i in range(len(pzero)):
            ps += combos[i][0] + "/" + combos[i][1] + ": " + str(round((1 - pzero[i]) * 1000) / 10) + "%\n"

        if any(pzero > 0.3):
            ps += "CAUTION: Limited price data used in simulation"

    filename = "pools/" + poolname + "/pooltext.txt"
    with open(filename, "w") as txt_file:
        txt_file.write(txt + "\n")
        txt_file.write(ps)

    return res


def getpool(poolname, D=None, src="cg", balanced=False):
    # Get current pool data
    print("[" + poolname + "] Fetching pool data...")
    if src == "cg":
        csv = "poolDF_cg.csv"
    else:
        csv = "poolDF_nomics.csv"

    pldata = pooldata(poolname, csv=csv, balanced=balanced)

    # Over-ride D if necessary
    if D is None:
        D = pldata["D"]
    else:
        D = int(D * 10**18)
        if isinstance(pldata["D"], list):  # if metapool
            pldata["D"][0] = D
            D = pldata["D"]

    if pldata["A_base"] is not None:
        A = [pldata["A"], pldata["A_base"]]
    else:
        A = pldata["A"]

    if pldata["fee_base"] is not None:
        fee = [pldata["fee"], pldata["fee_base"]]
    else:
        fee = pldata["fee"]

    if pldata["r"] is not None:
        r = int(pldata["r"].price[-1])
    else:
        r = None

    pl = pool(A, D, pldata["n"], fee=fee, tokens=pldata["tokens"], feemul=pldata["feemul"], r=r)
    pl.histvolume = pldata["histvolume"]
    pl.coins = pldata["coins"]

    return pl


# Functions to get pool data


def pooldata(poolname, csv="poolDF_cg.csv", balanced=False):  # noqa: C901
    w3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/aae0ec63797d4548bfe5c98c4f9aa230"))

    pools = pd.read_csv(
        csv,
        sep=";",
        header=0,
        index_col=0,
        converters={
            "coins": literal_eval,
            "precmul": literal_eval,
            "tokentype": literal_eval,
        },
    )
    p = pools.loc[poolname]

    ABItypes = ["uint256", "int128"]  # some old contracts used int128
    for ABItype in ABItypes:
        abi = (
            '[{"name":"A","outputs":[{"type":"uint256","name":""}],"inputs":[],"stateMutability":"view","type":"function","gas":5227},{"name":"balances","outputs":[{"type":"uint256","name":""}],"inputs":[{"type":"'  # noqa: E501
            + ABItype
            + '","name":"arg0"}],"stateMutability":"view","type":"function","gas":2250},{"name":"fee","outputs":[{"type":"uint256","name":""}],"inputs":[],"stateMutability":"view","type":"function","gas":2171},{"name":"get_virtual_price","outputs":[{"type":"uint256","name":""}],"inputs":[],"stateMutability":"view","type":"function","gas":1133537},{"name":"coins","outputs":[{"type":"address","name":""}],"inputs":[{"type":"'  # noqa: E501
            + ABItype
            + '","name":"arg0"}],"stateMutability":"view","type":"function","gas":2310}]'
        )
        contract = w3.eth.contract(address=p.address, abi=abi)
        try:
            contract.functions.balances(0).call()
            break
        except Exception:
            pass

    coins = p.coins

    if p.feemul == "None":
        feemul = None
    else:
        feemul = int(p.feemul)

    if p.precmul[0] == "r":
        # load redemption price data as r
        # update precmul based on redemption price
        r = redemptionprices(1000)
        p.precmul = [r.price[-1] / 10**18]
    else:
        r = None

    A = contract.functions.A().call()
    fee = contract.functions.fee().call()

    if p.basepool == "None":  # normal pool

        D = []
        for i in range(len(p.coins)):
            if p.tokentype:  # if any assets are ctokens/ytokens
                if p.tokentype[i]:  # if asset[i] is ctoken/ytoken
                    cAddress = contract.functions.coins(i).call()
                    rate = tokenrate(p.tokentype[i], cAddress)
                else:
                    rate = 10**18
            else:
                rate = 10**18

            D.append(contract.functions.balances(i).call() * p.precmul[i] * rate // 10**18)

        n = len(coins)
        A_base = None
        fee_base = None
        addresses = [p.address.lower()]

        pl = pool(A, D, n)
        D_balanced = pl.D()
        tokens = D_balanced * 10**18 // contract.functions.get_virtual_price().call()

        if balanced:
            D = D_balanced

    else:  # meta-pool
        basepool = pools.loc[p.basepool]

        for ABItype in ABItypes:
            abi = (
                '[{"name":"A","outputs":[{"type":"uint256","name":""}],"inputs":[],"stateMutability":"view","type":"function","gas":5227},{"name":"balances","outputs":[{"type":"uint256","name":""}],"inputs":[{"type":"'  # noqa: E501
                + ABItype
                + '","name":"arg0"}],"stateMutability":"view","type":"function","gas":2250},{"name":"fee","outputs":[{"type":"uint256","name":""}],"inputs":[],"stateMutability":"view","type":"function","gas":2171},{"name":"get_virtual_price","outputs":[{"type":"uint256","name":""}],"inputs":[],"stateMutability":"view","type":"function","gas":1133537},{"name":"coins","outputs":[{"type":"address","name":""}],"inputs":[{"type":"'  # noqa: E501
                + ABItype
                + '","name":"arg0"}],"stateMutability":"view","type":"function","gas":2310}]'
            )
            base_contract = w3.eth.contract(address=basepool.address, abi=abi)
            try:
                base_contract.functions.balances(0).call()
                break
            except Exception:
                pass

        D = []
        precmul = p.precmul
        precmul.append(base_contract.functions.get_virtual_price().call() / 10**18)
        for i in range(len(p.coins) + 1):
            D.append(int(contract.functions.balances(i).call() * precmul[i]))

        D_base = []
        for i in range(len(basepool.coins)):
            D_base.append(int(base_contract.functions.balances(i).call() * basepool.precmul[i]))

        D = [D, D_base]
        n = [len(p.coins) + 1, len(basepool.coins)]
        coins.extend(basepool.coins)
        A_base = base_contract.functions.A().call()
        fee_base = base_contract.functions.fee().call()
        addresses = [p.address.lower(), basepool.address.lower()]

        pl = pool([A, A_base], D, n)
        D_base_balanced = pl.basepool.D()
        tokens = D_base_balanced * 10**18 // base_contract.functions.get_virtual_price().call()

        if balanced:
            pl = pool([A, A_base], D, n, tokens=tokens)
            rates = pl.p[:]
            rates[pl.max_coin] = pl.basepool.get_virtual_price()
            if r is not None:
                rates[pl.max_coin - 1] = int(r.price[-1])
            xp = [x * p // 10**18 for x, p in zip(pl.x, rates)]
            D_balanced = pl.D(xp=xp)
            D = [D_balanced, D_base_balanced]

    # Get historical volume
    url = "https://api.thegraph.com/subgraphs/name/convex-community/volume-mainnet"

    histvolume = []
    for address in addresses:
        query = (
            """{
  swapVolumeSnapshots(
    where: {pool: "%s", period: 86400},
    orderBy: timestamp,
    orderDirection: desc,
    first:60
  ) {
    volume
  }
}"""
            % address
        )
        req = requests.post(url, json={"query": query})
        try:
            volume = pd.DataFrame(req.json()["data"]["swapVolumeSnapshots"], dtype="float").sum()[0]
        except Exception:
            print("[" + poolname + "] No historical volume info from Curve Subgraph.")
            volume = float(input("[" + poolname + "] Please input estimated volume for 2 months: "))
        histvolume.append(volume)

    histvolume = np.array(histvolume)

    # Format output as dict
    data = {
        "D": D,
        "coins": coins,
        "n": n,
        "A": A,
        "A_base": A_base,
        "fee": fee,
        "fee_base": fee_base,
        "tokens": tokens,
        "feemul": feemul,
        "histvolume": histvolume,
        "r": r,
    }

    return data


def tokenrate(tokentype, address):
    w3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/aae0ec63797d4548bfe5c98c4f9aa230"))

    if tokentype == "c":
        abi = '[{"constant":true,"inputs":[],"name":"exchangeRateStored","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"}]'  # noqa: E501
        contract = w3.eth.contract(address=address, abi=abi)
        rate = contract.functions.exchangeRateStored().call()

    elif tokentype == "y":
        abi = '[{"constant":true,"inputs":[],"name":"getPricePerFullShare","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"}]'  # noqa: E501
        contract = w3.eth.contract(address=address, abi=abi)
        rate = contract.functions.getPricePerFullShare().call()

    return rate


def redemptionprices(n=100):
    url = "https://api.thegraph.com/subgraphs/name/reflexer-labs/rai-mainnet"
    query = (
        """
{
  redemptionPrices(orderBy: timestamp, orderDirection: desc, first: %d) {
    timestamp
    value
  }
}"""
        % n
    )

    r = requests.post(url, json={"query": query})
    data = pd.DataFrame(r.json()["data"]["redemptionPrices"])
    data.columns = ["timestamp", "price"]
    data.price = (data.price.astype(float) * 10**18).astype(int)
    data.timestamp = pd.to_datetime(data.timestamp, unit="s", utc=True)
    data.sort_values("timestamp", inplace=True)
    data.set_index("timestamp", inplace=True)

    return data


# Plotters


def plotsims(A_list, ar, bal, pool_value, depth, volume, log_returns, err, show=True, saveas=False):
    """
    Plots output of Asims when only 1 fee is used

    """

    colors = plt.cm.viridis(np.linspace(0, 1, len(A_list)))

    # Summary stats
    fig, axs = plt.subplots(2, 3, constrained_layout=True, figsize=(8, 5))

    axs[0, 0].plot(ar.unstack(level=1) * 100, "k", zorder=1)
    axs[0, 0].scatter(A_list, ar * 100, c=colors, zorder=2)
    axs[0, 0].yaxis.set_major_formatter(mtick.PercentFormatter())
    axs[0, 0].set_xlabel("Amplitude (A)")
    axs[0, 0].set_ylabel("Annualized Returns")

    axs[0, 1].plot(A_list, np.median(depth, axis=1) * 100, "k", zorder=1, label="Med")
    axs[0, 1].plot(A_list, np.min(depth, axis=1) * 100, "k--", zorder=1, label="Min")
    axs[0, 1].scatter(A_list, np.median(depth, axis=1) * 100, c=colors, zorder=2)
    axs[0, 1].scatter(A_list, np.min(depth, axis=1) * 100, c=colors, zorder=2)
    axs[0, 1].yaxis.set_major_formatter(mtick.PercentFormatter())
    axs[0, 1].set_xlabel("Amplitude (A)")
    axs[0, 1].set_ylabel("Price Depth (.1%)")
    axs[0, 1].legend(loc="lower right")

    axs[0, 2].plot(A_list, bal.median(axis=1), "k", zorder=1, label="Med")
    axs[0, 2].plot(A_list, bal.min(axis=1), "k--", zorder=1, label="Min")
    axs[0, 2].scatter(A_list, bal.median(axis=1), c=colors, zorder=2)
    axs[0, 2].scatter(A_list, bal.min(axis=1), c=colors, zorder=2)
    axs[0, 2].set_ylim([0, 1])
    axs[0, 2].set_xlabel("Amplitude (A)")
    axs[0, 2].set_ylabel("Pool Balance")
    axs[0, 2].legend(loc="lower right")

    axs[1, 0].plot(A_list, volume.sum(axis=1) / 60, "k", zorder=1)
    axs[1, 0].scatter(A_list, volume.sum(axis=1) / 60, c=colors, zorder=2)
    axs[1, 0].set_xlabel("Amplitude (A)")
    axs[1, 0].set_ylabel("Daily Volume")

    axs[1, 1].plot(A_list, err.median(axis=1), "k", zorder=1)
    axs[1, 1].scatter(A_list, err.median(axis=1), c=colors, zorder=2)
    axs[1, 1].set_xlabel("Amplitude (A)")
    axs[1, 1].set_ylabel("Median Price Error")

    # Legend
    handles = []
    for i in range(len(colors)):
        handles.append(
            Line2D(
                [0],
                [0],
                marker="o",
                color="w",
                markerfacecolor=colors[i],
                markersize=10,
            )
        )

    axs[1, 2].legend(handles, A_list, title="Amplitude", ncol=2)
    axs[1, 2].axis("off")

    if saveas:
        plt.savefig(saveas + "_1.png")

    # Time-series Data
    fig, axs = plt.subplots(3, 2, constrained_layout=True, figsize=(8, 5))

    # Pool value
    for i in range(len(colors)):
        axs[0, 0].plot(pool_value.iloc[i], color=colors[i])

    axs[0, 0].set_ylabel("Pool Value")
    plt.setp(axs[0, 0].xaxis.get_majorticklabels(), rotation=40, ha="right")
    axs[0, 0].yaxis.get_major_formatter().set_useOffset(False)

    # Balance
    for i in range(len(colors)):
        axs[0, 1].plot(bal.iloc[i], color=colors[i])

    axs[0, 1].set_ylabel("Pool Balance")
    plt.setp(axs[0, 1].xaxis.get_majorticklabels(), rotation=40, ha="right")

    # Volume
    for i in range(len(colors)):
        axs[1, 0].plot(volume.T.resample("1D").sum().T.iloc[i], color=colors[i])

    axs[1, 0].set_ylabel("Daily Volume")
    plt.setp(axs[1, 0].xaxis.get_majorticklabels(), rotation=40, ha="right")

    # Depth
    for i in range(len(colors)):
        axs[1, 1].plot(depth.iloc[i] * 100, color=colors[i])

    axs[1, 1].set_ylabel("Price Depth")
    axs[1, 1].yaxis.set_major_formatter(mtick.PercentFormatter())
    plt.setp(axs[1, 1].xaxis.get_majorticklabels(), rotation=40, ha="right")

    # Distribution of log returns
    axs[2, 0].hist(log_returns.T, 30, histtype="step", color=colors)
    axs[2, 0].set_xlabel("Log Returns")
    axs[2, 0].set_ylabel("Frequency")

    # Price error
    axs[2, 1].hist(err.T, 30, histtype="step", color=colors)
    axs[2, 1].set_xlabel("Price Error")
    axs[2, 1].set_ylabel("Frequency")

    if saveas:
        plt.savefig(saveas + "_2.png")

    if show:
        plt.show()


def plotsimsfee(A_list, fee_list, ar, bal, depth, volume, err, show=True, saveas=False):
    """
    Plots 2D summary output of Asims when multiple fees are used

    """
    fig, axs = plt.subplots(2, 3, constrained_layout=True, figsize=(11, 5.5))
    fee_list_pct = np.array(fee_list) / 10**8

    # Annualized Returns
    im = axs[0, 0].imshow(ar.unstack("fee") * 100, cmap="plasma")
    axs[0, 0].set_title("Annualized Returns (%)")
    axs[0, 0].set_xlabel("Fee (%)")
    axs[0, 0].set_ylabel("Amplitude (A)")
    axs[0, 0].set_xticks(np.arange(len(fee_list)))
    axs[0, 0].set_yticks(np.arange(len(A_list)))
    axs[0, 0].set_xticklabels(fee_list_pct)
    axs[0, 0].set_yticklabels(A_list)
    plt.setp(axs[0, 0].xaxis.get_majorticklabels(), rotation=90)
    cbar = fig.colorbar(im, ax=axs[0, 0])

    # Volume
    im = axs[1, 0].imshow(volume.sum(axis=1).unstack("fee"), cmap="plasma")
    axs[1, 0].set_title("Volume")
    axs[1, 0].set_xlabel("Fee (%)")
    axs[1, 0].set_ylabel("Amplitude (A)")
    axs[1, 0].set_xticks(np.arange(len(fee_list)))
    axs[1, 0].set_yticks(np.arange(len(A_list)))
    axs[1, 0].set_xticklabels(fee_list_pct)
    axs[1, 0].set_yticklabels(A_list)
    plt.setp(axs[1, 0].xaxis.get_majorticklabels(), rotation=90)
    cbar = fig.colorbar(im, ax=axs[1, 0])

    # Median Depth
    im = axs[0, 1].imshow(depth.median(axis=1).unstack("fee") * 100, cmap="plasma")
    axs[0, 1].set_title("Med. Depth (.1%)")
    axs[0, 1].set_xlabel("Fee (%)")
    axs[0, 1].set_ylabel("Amplitude (A)")
    axs[0, 1].set_xticks(np.arange(len(fee_list)))
    axs[0, 1].set_yticks(np.arange(len(A_list)))
    axs[0, 1].set_xticklabels(fee_list_pct)
    axs[0, 1].set_yticklabels(A_list)
    plt.setp(axs[0, 1].xaxis.get_majorticklabels(), rotation=90)
    cbar = fig.colorbar(im, ax=axs[0, 1])
    cbar.ax.yaxis.set_major_formatter(mtick.PercentFormatter())

    # Minimum Depth
    im = axs[1, 1].imshow(depth.min(axis=1).unstack("fee") * 100, cmap="plasma")
    axs[1, 1].set_title("Min. Depth (.1%)")
    axs[1, 1].set_xlabel("Fee (%)")
    axs[1, 1].set_ylabel("Amplitude (A)")
    axs[1, 1].set_xticks(np.arange(len(fee_list)))
    axs[1, 1].set_yticks(np.arange(len(A_list)))
    axs[1, 1].set_xticklabels(fee_list_pct)
    axs[1, 1].set_yticklabels(A_list)
    plt.setp(axs[1, 1].xaxis.get_majorticklabels(), rotation=90)
    cbar = fig.colorbar(im, ax=axs[1, 1])
    cbar.ax.yaxis.set_major_formatter(mtick.PercentFormatter())

    # Median Balance
    im = axs[0, 2].imshow(bal.median(axis=1).unstack("fee"), cmap="plasma")
    axs[0, 2].set_title("Median Balance")
    axs[0, 2].set_xlabel("Fee (%)")
    axs[0, 2].set_ylabel("Amplitude (A)")
    axs[0, 2].set_xticks(np.arange(len(fee_list)))
    axs[0, 2].set_yticks(np.arange(len(A_list)))
    axs[0, 2].set_xticklabels(fee_list_pct)
    axs[0, 2].set_yticklabels(A_list)
    plt.setp(axs[0, 2].xaxis.get_majorticklabels(), rotation=90)
    cbar = fig.colorbar(im, ax=axs[0, 2])

    # Minimum Balance
    im = axs[1, 2].imshow(bal.min(axis=1).unstack("fee"), cmap="plasma")
    axs[1, 2].set_title("Minimum Balance")
    axs[1, 2].set_xlabel("Fee (%)")
    axs[1, 2].set_ylabel("Amplitude (A)")
    axs[1, 2].set_xticks(np.arange(len(fee_list)))
    axs[1, 2].set_yticks(np.arange(len(A_list)))
    axs[1, 2].set_xticklabels(fee_list_pct)
    axs[1, 2].set_yticklabels(A_list)
    plt.setp(axs[1, 2].xaxis.get_majorticklabels(), rotation=90)
    cbar = fig.colorbar(im, ax=axs[1, 2])

    if saveas:
        plt.savefig(saveas + ".png")

    if show:
        plt.show()


def saveplots(poolname, A_list, fee_list, ar, bal, depth, volume, pool_value, log_returns, err):
    if not os.path.exists("pools/" + poolname):
        os.makedirs("pools/" + poolname)

    if len(fee_list) > 1:
        plotsimsfee(
            A_list,
            fee_list,
            ar,
            bal,
            depth,
            volume,
            err,
            show=False,
            saveas="pools/" + poolname + "/summary",
        )

    for curr_fee in fee_list:
        filename = "pools/" + poolname + "/fee_" + str(round(curr_fee) / 10**8)[2:].ljust(2, "0")

        plotsims(
            A_list,
            ar.loc[(slice(None), curr_fee), :],
            bal.loc[(slice(None), curr_fee), :],
            pool_value.loc[(slice(None), curr_fee), :],
            depth.loc[(slice(None), curr_fee), :],
            volume.loc[(slice(None), curr_fee), :],
            log_returns.loc[(slice(None), curr_fee), :],
            err.loc[(slice(None), curr_fee), :],
            show=False,
            saveas=filename,
        )

        plt.close("all")


# Error functions for optarb and optarbs
def arberror(dx, pool, i, j, p):
    dx = int(dx)

    x_old = pool.x[:]
    if pool.ismeta:
        x_old_base = pool.basepool.x[:]
        tokens_old = pool.basepool.tokens

    pool.exchange(i, j, dx)  # do trade

    # Check price error after trade
    # Error = pool price (dy/dx) - external price (p);
    error = pool.dydxfee(i, j, 10**12) - p

    pool.x = x_old
    if pool.ismeta:
        pool.basepool.x = x_old_base
        pool.basepool.tokens = tokens_old

    return error


def arberrors(dxs, pool, price_targs, coins):
    x_old = pool.x[:]
    if pool.ismeta:
        x_old_base = pool.basepool.x[:]
        tokens_old = pool.basepool.tokens

    # Do each trade
    k = 0
    for pair in coins:
        i = pair[0]
        j = pair[1]

        if np.isnan(dxs[k]):
            dx = 0
        else:
            dx = int(dxs[k])

        if dx > 0:
            pool.exchange(i, j, dx)

        k += 1

    # Check price errors after all trades
    errors = []
    k = 0
    for pair in coins:
        i = pair[0]
        j = pair[1]
        p = price_targs[k]
        errors.append(pool.dydxfee(i, j, 10**12) - p)
        k += 1

    pool.x = x_old
    if pool.ismeta:
        pool.basepool.x = x_old_base
        pool.basepool.tokens = tokens_old

    return errors
