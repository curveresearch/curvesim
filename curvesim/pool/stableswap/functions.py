from math import prod

from gmpy2 import mpz


def get_xp(x, p):
    return [x * p // 10**18 for x, p in zip(x, p)]


def get_virtual_price(xp, A, tokens):
    return get_D(xp, A) * 10**18 // tokens


def get_D(xp, A):
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
    n = len(xp)
    Ann = A * n
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


def get_D_mem(rates, balances, A, xp=None):
    xp = xp or get_xp(balances, rates)
    return get_D(xp, A)


def exchange(i, j, dx, x, p, A, fee, admin_fee, xp=None, fee_mul=None):
    xp = xp or get_xp(x, p)
    x_i = xp[i] + dx * p[i] // 10**18
    y = get_y(i, j, x_i, xp, A)
    dy = xp[j] - y - 1

    if fee_mul is None:
        fee = dy * fee // 10**10
    else:
        fee = (
            dy
            * dynamic_fee((xp[i] + x_i) // 2, (xp[j] + y) // 2, fee, fee_mul)
            // 10**10
        )

    admin_fee = fee * admin_fee // 10**10

    # Convert all to real units
    rate = p[j]
    dy = (dy - fee) * 10**18 // rate
    fee = fee * 10**18 // rate
    admin_fee = admin_fee * 10**18 // rate
    assert dy >= 0

    x = x[:]
    x[i] += dx
    x[j] -= dy + admin_fee

    return x, dy, fee, admin_fee


def exchange_underlying(
    i,
    j,
    dx,
    x,
    x_base,
    rates,
    rates_base,
    A,
    A_base,
    max_coin,
    tokens_base,
    fee,
    fee_base,
    admin_fee,
    base_xp=None,
):
    # Use base_i or base_j if they are >= 0
    base_i = i - max_coin
    base_j = j - max_coin
    meta_i = max_coin
    meta_j = max_coin
    if base_i < 0:
        meta_i = i
    if base_j < 0:
        meta_j = j

    if base_i < 0 or base_j < 0:  # if i or j not in basepool
        xp = [x * p // 10**18 for x, p in zip(x, rates)]

        if base_i < 0:
            x_i = xp[i] + dx * rates[i] // 10**18
        else:
            # i is from BasePool
            # At first, get the amount of pool tokens
            n_base = len(x_base)
            base_inputs = [0] * n_base
            base_inputs[base_i] = dx
            # Deposit and measure delta
            x_base, tokens_base, dx, _ = add_liquidity(
                base_inputs,
                A_base,
                x_base,
                rates_base,
                tokens_base,
                fee_base,
                admin_fee,
                xp=base_xp,
            )

            # Need to convert pool token to "virtual" units using rates
            x_i = dx * rates[max_coin] // 10**18
            # Adding number of pool tokens
            x_i += xp[max_coin]

        y = get_y(meta_i, meta_j, x_i, xp, A)

        # Either a real coin or token
        dy = xp[meta_j] - y - 1
        dy_fee = dy * fee // 10**10

        # Convert all to real units
        # Works for both pool coins and real coins
        dy = (dy - dy_fee) * 10**18 // rates[meta_j]

        dy_admin_fee = dy_fee * admin_fee // 10**10
        dy_admin_fee = dy_admin_fee * 10**18 // rates[meta_j]

        dy_fee = dy_fee * 10**18 // rates[meta_j]

        # Change balances exactly in same way as we change actual ERC20 coin amounts
        x = x[:]
        x[meta_i] += dx
        # When rounding errors happen, we undercharge admin fee in favor of LP
        x[meta_j] -= dy + dy_admin_fee

        # Withdraw from the base pool if needed
        if base_j >= 0:
            x_base, tokens_base, dy, dy_fee, admin_fee = remove_liquidity_one_coin(
                dy,
                base_j,
                A_base,
                x_base,
                rates_base,
                tokens_base,
                fee_base,
                admin_fee,
                xp=base_xp,
            )
    else:
        # If both are from the base pool
        x_base, dy, dy_fee, dy_admin_fee = exchange(
            base_i,
            base_j,
            dx,
            x_base,
            rates_base,
            A_base,
            fee_base,
            admin_fee,
            xp=base_xp,
        )

    return x, x_base, tokens_base, dy, dy_fee, dy_admin_fee


def get_y(i, j, xp_i, xp, A):
    """
    Calculate x[j] if one makes x[i] = x

    Done by solving quadratic equation iteratively.
    x_1**2 + x1 * (sum' - (A * n - 1) * D / (A * n)) = D**(n + 1)/(n**(n + 1) * prod' * A)
    x_1**2 + b*x_1 = c

    x_1 = (x_1**2 + c) / (2*x_1 + b)
    """
    n = len(xp)
    xx = xp[:]
    D = get_D(xx, A)
    D = mpz(D)
    xx[i] = xp_i  # x is quantity of underlying asset brought to 1e18 precision
    xx = [xx[k] for k in range(n) if k != j]
    Ann = A * n
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


def dynamic_fee(xpi, xpj, fee, fee_mul):
    xps2 = xpi + xpj
    xps2 *= xps2  # Doing just ** 2 can overflow apparently
    return (fee_mul * fee) // ((fee_mul - 10**10) * 4 * xpi * xpj // xps2 + 10**10)


def dydx_metapool(
    i,
    j,
    x,
    x_base,
    rates,
    rates_base,
    A,
    A_base,
    max_coin,
    tokens_base,
    fee=None,
    fee_base=None,
    base_xp=None,
    dx=10**12,
):
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
    base_i = i - max_coin
    base_j = j - max_coin
    base_xp = base_xp or [mpz(x) * p // 10**18 for x, p in zip(x_base, rates_base)]

    # both in and out tokens are in basepool
    if base_i >= 0 and base_j >= 0:
        _dydx = dydx(base_i, base_j, base_xp, A_base, fee=fee_base)
        return float(_dydx)

    xp = [mpz(x) * p // 10**18 for x, p in zip(x, rates)]

    x_prod = prod(base_xp)
    n = len(base_xp)
    D = mpz(get_D(base_xp, A_base))
    D_pow = D ** (n + 1)
    A_pow = A_base * n ** (n + 1)

    if base_i < 0:  # i is primary
        xj = base_xp[base_j]
        D_prime = (
            -1
            * (A_pow * x_prod + D_pow / xj)
            / (n**n * x_prod - A_pow * x_prod - (n + 1) * D**n)
        )
        D_prime = float(D_prime)

        dwdz = dydx(0, max_coin, xp, A, fee=fee)

        _dydx = dwdz / D_prime

        if fee_base:
            fee = fee_base - fee_base * xj // sum(base_xp) + 5 * 10**5
        else:
            fee = 0
        _dydx *= 1 - fee / 10**10

    else:  # i is from basepool
        base_inputs = [0] * n
        base_inputs[base_i] = dx * 10**18 // rates_base[base_i]

        dw = calc_token_amount(
            base_inputs, A_base, x_base, rates_base, tokens_base, fee=fee_base
        )
        if fee_base:
            dw = dw[0]
        # Convert lp token amount to virtual units
        dw = dw * rates[max_coin] // 10**18
        x = xp[max_coin] + dw

        meta_i = max_coin
        meta_j = j
        y = get_y(meta_i, meta_j, x, xp, A)

        dy = xp[meta_j] - y - 1
        if fee:
            dy_fee = dy * fee // 10**10
        else:
            dy_fee = 0
        dy -= dy_fee

        _dydx = dy / dx

    return float(_dydx)


def dydx(i, j, xp, A, fee=None, fee_mul=None, **kwargs):
    """
    Treats indices as applying to the "top-level" pool if a metapool.
    Basically this is the "regular" pricing calc with no special metapool handling.
    """
    xi = xp[i]
    xj = xp[j]
    n = len(xp)
    D = get_D(xp, A)
    D_pow = mpz(D) ** (n + 1)
    x_prod = prod(xp)
    A_pow = A * n ** (n + 1)
    dydx = (xj * (xi * A_pow * x_prod + D_pow)) / (xi * (xj * A_pow * x_prod + D_pow))

    if fee:
        if fee_mul is None:
            fee_factor = fee / 10**10
        else:
            dx = 10**12
            fee_factor = (
                dynamic_fee(xi + dx // 2, xj - int(dydx * dx) // 2, fee, fee_mul)
                / 10**10
            )
    else:
        fee_factor = 0

    dydx *= 1 - fee_factor

    return float(dydx)


def dydx_metapool_rai(*args, **kwargs):
    i, j = args[0:2]
    rates, rates_base = args[4:6]
    max_coin = args[8]

    dydx = dydx_metapool(*args, **kwargs)

    if i >= max_coin and j < max_coin:
        base_i = i - max_coin
        dydx = dydx * rates_base[base_i] / rates[j]

    if j >= max_coin and i < max_coin:
        base_j = j - max_coin
        dydx = dydx * rates[i] / rates_base[base_j]

    return dydx


def dydx_rai(*args, p=None, **kwargs):
    i, j = args[0:2]
    _dydx = dydx(*args, **kwargs)
    return _dydx * p[i] / p[j]


def add_liquidity(amounts, A, x, rates, tokens, fee, admin_fee, xp=None):
    mint_amount, fees = calc_token_amount(amounts, A, x, rates, tokens, fee=fee, xp=xp)
    tokens += mint_amount

    admin_fees = [f * admin_fee // 10**10 for f in fees]

    new_balances = [bal + amt - fee for bal, amt, fee in zip(x, amounts, admin_fees)]

    return new_balances, tokens, mint_amount, admin_fees


def remove_liquidity_one_coin(
    token_amount, i, A, x, p, tokens, fee, admin_fee, xp=None
):
    xp = xp or get_xp(x, p)
    dy, dy_fee = calc_withdraw_one_coin(token_amount, i, A, xp, p, tokens, fee=fee)

    admin_fee = dy_fee * admin_fee // 10**10

    x = x[:]
    x[i] -= dy + admin_fee
    tokens -= token_amount

    return x, tokens, dy, dy_fee, admin_fee


def calc_token_amount(amounts, A, x, rates, tokens, fee=False, xp=None):
    """
    Fee logic is based on add_liquidity, which makes this more accurate than
    the `calc_token_amount` in the actual contract, which neglects fees.

    By default, it's assumed you want the contract behavior.
    """
    n = len(x)
    old_balances = x
    D0 = get_D_mem(rates, old_balances, A, xp=xp)

    new_balances = x[:]
    for i in range(n):
        new_balances[i] += amounts[i]
    D1 = get_D_mem(rates, new_balances, A)

    mint_balances = new_balances[:]

    if fee:
        _fee = fee * n // (4 * (n - 1))

        fees = [0] * n
        for i in range(n):
            ideal_balance = D1 * old_balances[i] // D0
            difference = abs(ideal_balance - new_balances[i])
            fees[i] = _fee * difference // 10**10
            mint_balances[i] -= fees[i]

    D2 = get_D_mem(rates, mint_balances, A)

    mint_amount = tokens * (D2 - D0) // D0
    if fee:
        return mint_amount, fees
    else:
        return mint_amount


def calc_withdraw_one_coin(token_amount, i, A, xp, p, tokens, fee=False):
    A = A
    n = len(xp)
    D0 = get_D(xp, A)
    D1 = D0 - token_amount * D0 // tokens

    new_y = get_y_D(A, i, xp, D1)
    dy_before_fee = (xp[i] - new_y) * 10**18 // p[i]

    xp_reduced = xp
    if fee:
        n_coins = n
        _fee = fee * n_coins // (4 * (n_coins - 1))

        for j in range(n_coins):
            dx_expected = 0
            if j == i:
                dx_expected = xp[j] * D1 // D0 - new_y
            else:
                dx_expected = xp[j] - xp[j] * D1 // D0
            xp_reduced[j] -= _fee * dx_expected // 10**10

    dy = xp[i] - get_y_D(A, i, xp_reduced, D1)
    dy = (dy - 1) * 10**18 // p[i]
    if fee:
        dy_fee = dy_before_fee - dy
        return dy, dy_fee
    else:
        return dy


def get_y_D(A, i, xp, D):
    """
    Calculate x[j] if one makes x[i] = x

    Done by solving quadratic equation iteratively.
    x_1**2 + x1 * (sum' - (A*n**n - 1) * D / (A * n**n)) = D ** (n+1)/(n ** (2 * n) * prod' * A)
    x_1**2 + b*x_1 = c

    x_1 = (x_1**2 + c) / (2*x_1 + b)
    """
    n = len(xp)
    D = mpz(D)
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
