"""
@title StableSwap
@author Curve.Fi
@license Copyright (c) Curve.Fi, 2020-2022 - all rights reserved
@notice Pool for DAI/USDC/USDT
"""
from vyper.interfaces import ERC20

interface CurveToken:
    def totalSupply() -> uint256: view
    def mint(_to: address, _value: uint256) -> bool: nonpayable
    def burnFrom(_to: address, _value: uint256) -> bool: nonpayable

# Events
event TokenExchange:
    buyer: indexed(address)
    sold_id: uint256
    tokens_sold: uint256
    bought_id: uint256
    tokens_bought: uint256

event AddLiquidity:
    provider: indexed(address)
    token_amounts: uint256[N_COINS]
    fees: uint256[N_COINS]
    invariant: uint256
    token_supply: uint256

event RemoveLiquidity:
    provider: indexed(address)
    token_amounts: uint256[N_COINS]
    fees: uint256[N_COINS]
    token_supply: uint256

event RemoveLiquidityOne:
    provider: indexed(address)
    token_amount: uint256
    coin_amount: uint256

event RemoveLiquidityImbalance:
    provider: indexed(address)
    token_amounts: uint256[N_COINS]
    fees: uint256[N_COINS]
    invariant: uint256
    token_supply: uint256


# sim: made public for pool sim testing
N_COINS: public(constant(uint256)) = 3

FEE_DENOMINATOR: constant(uint256) = 10 ** 10
LENDING_PRECISION: constant(uint256) = 10 ** 18
PRECISION: constant(uint256) = 10 ** 18  # The precision to convert to
PRECISION_MUL: constant(uint256[N_COINS]) = [1, 1000000000000, 1000000000000]
RATES: constant(uint256[N_COINS]) = [1000000000000000000, 1000000000000000000000000000000, 1000000000000000000000000000000]
FEE_INDEX: constant(uint256) = 2  # Which coin may potentially have fees (USDT)


owner: public(address)
token: public(CurveToken)

initial_A: public(uint256)
future_A: public(uint256)
initial_A_time: public(uint256)
future_A_time: public(uint256)

coins: public(address[N_COINS])
balances: public(uint256[N_COINS])
fee: public(uint256)  # fee * 1e10
admin_fee: public(uint256)  # admin_fee * 1e10


@external
def __init__(
    _owner: address,
    _coins: address[N_COINS],
    _pool_token: address,
    _A: uint256,
    _fee: uint256,
    _admin_fee: uint256
):
    """
    @notice Contract constructor
    @param _owner Contract owner address
    @param _coins Addresses of ERC20 conracts of coins
    @param _pool_token Address of the token representing LP share
    @param _A Amplification coefficient multiplied by n * (n - 1)
    @param _fee Fee to charge for exchanges
    @param _admin_fee Admin fee
    """
    for i in range(N_COINS):
        assert _coins[i] != ZERO_ADDRESS
    self.coins = _coins
    self.initial_A = _A
    self.future_A = _A
    self.fee = _fee
    self.admin_fee = _admin_fee
    self.owner = _owner
    self.token = CurveToken(_pool_token)


# sim: function added for pool sim testing
@pure
@external
def rates(i: uint256) -> uint256:
    return RATES[i]


# sim: function added for pool sim testing
@view
@external
def D() -> uint256:
    A: uint256 = self._A()
    xp: uint256[N_COINS] = self._xp()
    return self.get_D(xp, A)


@pure
@internal
def get_D(xp: uint256[N_COINS], amp: uint256) -> uint256:
    S: uint256 = 0
    for _x in xp:
        S += _x
    if S == 0:
        return 0

    Dprev: uint256 = 0
    D: uint256 = S
    Ann: uint256 = amp * N_COINS
    for _i in range(255):
        D_P: uint256 = D
        for _x in xp:
            D_P = D_P * D / (_x * N_COINS)  # If division by 0, this will be borked: only withdrawal will work. And that is good
        Dprev = D
        D = (Ann * S + D_P * N_COINS) * D / ((Ann - 1) * D + (N_COINS + 1) * D_P)
        # Equality with the precision of 1
        if D > Dprev:
            if D - Dprev <= 1:
                break
        else:
            if Dprev - D <= 1:
                break
    return D


@view
@internal
def get_D_mem(_balances: uint256[N_COINS], amp: uint256) -> uint256:
    return self.get_D(self._xp_mem(_balances), amp)


@view
@external
def get_virtual_price() -> uint256:
    """
    Returns portfolio virtual price (for calculating profit)
    scaled up by 1e18
    """
    D: uint256 = self.get_D(self._xp(), self._A())
    # D is in the units similar to DAI (e.g. converted to precision 1e18)
    # When balanced, D = n * x_u - total virtual value of the portfolio
    token_supply: uint256 = self.token.totalSupply()
    return D * PRECISION / token_supply


@view
@external
def calc_token_amount(amounts: uint256[N_COINS], deposit: bool) -> uint256:
    """
    Simplified method to calculate addition or reduction in token supply at
    deposit or withdrawal without taking fees into account (but looking at
    slippage).
    Needed to prevent front-running, not for precise calculations!
    """
    _balances: uint256[N_COINS] = self.balances
    amp: uint256 = self._A()
    D0: uint256 = self.get_D_mem(_balances, amp)
    for i in range(N_COINS):
        if deposit:
            _balances[i] += amounts[i]
        else:
            _balances[i] -= amounts[i]
    D1: uint256 = self.get_D_mem(_balances, amp)
    token_amount: uint256 = self.token.totalSupply()
    diff: uint256 = 0
    if deposit:
        diff = D1 - D0
    else:
        diff = D0 - D1
    return diff * token_amount / D0


@external
@nonreentrant('lock')
def add_liquidity(amounts: uint256[N_COINS], min_mint_amount: uint256) -> uint256:
    fees: uint256[N_COINS] = empty(uint256[N_COINS])
    _fee: uint256 = self.fee * N_COINS / (4 * (N_COINS - 1))
    _admin_fee: uint256 = self.admin_fee
    amp: uint256 = self._A()

    token_supply: uint256 = self.token.totalSupply()
    # Initial invariant
    D0: uint256 = 0
    old_balances: uint256[N_COINS] = self.balances
    if token_supply > 0:
        D0 = self.get_D_mem(old_balances, amp)
    new_balances: uint256[N_COINS] = old_balances

    for i in range(N_COINS):
        in_amount: uint256 = amounts[i]
        if token_supply == 0:
            assert in_amount > 0  # dev: initial deposit requires all coins
        # sim: comment-out the interaction with coins.
        # Life is a lot easier for us if we don't bother traversing
        # this code path with mocks and such.
        # ----------------------------------------------------------
        # in_coin: address = self.coins[i]

        # # Take coins from the sender
        # if in_amount > 0:
        #     if i == FEE_INDEX:
        #         in_amount = ERC20(in_coin).balanceOf(self)

        #     # "safeTransferFrom" which works for ERC20s which return bool or not
        #     _response: Bytes[32] = raw_call(
        #         in_coin,
        #         concat(
        #             method_id("transferFrom(address,address,uint256)"),
        #             convert(msg.sender, bytes32),
        #             convert(self, bytes32),
        #             convert(amounts[i], bytes32),
        #         ),
        #         max_outsize=32,
        #     )  # dev: failed transfer
        #     if len(_response) > 0:
        #         assert convert(_response, bool)  # dev: failed transfer

        #     if i == FEE_INDEX:
        #         in_amount = ERC20(in_coin).balanceOf(self) - in_amount

        new_balances[i] = old_balances[i] + in_amount

    # Invariant after change
    D1: uint256 = self.get_D_mem(new_balances, amp)
    assert D1 > D0

    # We need to recalculate the invariant accounting for fees
    # to calculate fair user's share
    D2: uint256 = D1
    if token_supply > 0:
        # Only account for fees if we are not the first to deposit
        for i in range(N_COINS):
            ideal_balance: uint256 = D1 * old_balances[i] / D0
            difference: uint256 = 0
            if ideal_balance > new_balances[i]:
                difference = ideal_balance - new_balances[i]
            else:
                difference = new_balances[i] - ideal_balance
            fees[i] = _fee * difference / FEE_DENOMINATOR
            self.balances[i] = new_balances[i] - (fees[i] * _admin_fee / FEE_DENOMINATOR)
            new_balances[i] -= fees[i]
        D2 = self.get_D_mem(new_balances, amp)
    else:
        self.balances = new_balances

    # Calculate, how much pool tokens to mint
    mint_amount: uint256 = 0
    if token_supply == 0:
        mint_amount = D1  # Take the dust if there was any
    else:
        mint_amount = token_supply * (D2 - D0) / D0

    assert mint_amount >= min_mint_amount, "Slippage screwed you"

    # Mint pool tokens
    self.token.mint(msg.sender, mint_amount)

    log AddLiquidity(msg.sender, amounts, fees, D1, token_supply + mint_amount)

    return mint_amount



@view
@internal
def get_y(i: uint256, j: uint256, x: uint256, xp_: uint256[N_COINS]) -> uint256:
    # x in the input is converted to the same price/precision

    assert i != j       # dev: same coin
    assert j >= 0       # dev: j below zero
    assert j < N_COINS  # dev: j above N_COINS

    # should be unreachable, but good for safety
    assert i >= 0
    assert i < N_COINS

    amp: uint256 = self._A()
    D: uint256 = self.get_D(xp_, amp)
    c: uint256 = D
    S_: uint256 = 0
    Ann: uint256 = amp * N_COINS

    _x: uint256 = 0
    for _i in range(N_COINS):
        if _i == i:
            _x = x
        elif _i != j:
            _x = xp_[_i]
        else:
            continue
        S_ += _x
        c = c * D / (_x * N_COINS)
    c = c * D / (Ann * N_COINS)
    b: uint256 = S_ + D / Ann  # - D
    y_prev: uint256 = 0
    y: uint256 = D
    for _i in range(255):
        y_prev = y
        y = (y*y + c) / (2 * y + b - D)
        # Equality with the precision of 1
        if y > y_prev:
            if y - y_prev <= 1:
                break
        else:
            if y_prev - y <= 1:
                break
    return y


@external
@nonreentrant('lock')
def exchange(i: uint256, j: uint256, dx: uint256, min_dy: uint256) -> uint256:
    rates: uint256[N_COINS] = RATES

    old_balances: uint256[N_COINS] = self.balances
    xp: uint256[N_COINS] = self._xp_mem(old_balances)

    # Handling an unexpected charge of a fee on transfer (USDT, PAXG)
    dx_w_fee: uint256 = dx
    # sim: comment-out the interaction with coins.
    # Life is a lot easier for us if we don't bother traversing
    # this code path with mocks and such.
    # ----------------------------------------------------------
    # input_coin: address = self.coins[i]

    # if i == FEE_INDEX:
    #     dx_w_fee = ERC20(input_coin).balanceOf(self)

    # # "safeTransferFrom" which works for ERC20s which return bool or not
    # _response: Bytes[32] = raw_call(
    #     input_coin,
    #     concat(
    #         method_id("transferFrom(address,address,uint256)"),
    #         convert(msg.sender, bytes32),
    #         convert(self, bytes32),
    #         convert(dx, bytes32),
    #     ),
    #     max_outsize=32,
    # )  # dev: failed transfer
    # if len(_response) > 0:
    #     assert convert(_response, bool)  # dev: failed transfer

    # if i == FEE_INDEX:
    #     dx_w_fee = ERC20(input_coin).balanceOf(self) - dx_w_fee

    x: uint256 = xp[i] + dx_w_fee * rates[i] / PRECISION
    y: uint256 = self.get_y(i, j, x, xp)

    dy: uint256 = xp[j] - y - 1  # -1 just in case there were some rounding errors
    dy_fee: uint256 = dy * self.fee / FEE_DENOMINATOR

    # Convert all to real units
    dy = (dy - dy_fee) * PRECISION / rates[j]
    assert dy >= min_dy, "Exchange resulted in fewer coins than expected"

    dy_admin_fee: uint256 = dy_fee * self.admin_fee / FEE_DENOMINATOR
    dy_admin_fee = dy_admin_fee * PRECISION / rates[j]

    # Change balances exactly in same way as we change actual ERC20 coin amounts
    self.balances[i] = old_balances[i] + dx_w_fee
    # When rounding errors happen, we undercharge admin fee in favor of LP
    self.balances[j] = old_balances[j] - dy - dy_admin_fee

    # sim: comment-out the interaction with coins.
    # Life is a lot easier for us if we don't bother traversing
    # this code path with mocks and such.
    # ----------------------------------------------------------
    # # "safeTransfer" which works for ERC20s which return bool or not
    # _response = raw_call(
    #     self.coins[j],
    #     concat(
    #         method_id("transfer(address,uint256)"),
    #         convert(msg.sender, bytes32),
    #         convert(dy, bytes32),
    #     ),
    #     max_outsize=32,
    # )  # dev: failed transfer
    # if len(_response) > 0:
    #     assert convert(_response, bool)  # dev: failed transfer

    log TokenExchange(msg.sender, i, dx, j, dy)

    return dy

@view
@internal
def _A() -> uint256:
    """
    Handle ramping A up or down
    """
    t1: uint256 = self.future_A_time
    A1: uint256 = self.future_A

    if block.timestamp < t1:
        A0: uint256 = self.initial_A
        t0: uint256 = self.initial_A_time
        # Expressions in uint256 cannot have negative numbers, thus "if"
        if A1 > A0:
            return A0 + (A1 - A0) * (block.timestamp - t0) / (t1 - t0)
        else:
            return A0 - (A0 - A1) * (block.timestamp - t0) / (t1 - t0)

    else:  # when t1 == 0 or block.timestamp >= t1
        return A1


@view
@internal
def get_y_D(A_: uint256, i: uint256, xp: uint256[N_COINS], D: uint256) -> uint256:
    """
    Calculate x[i] if one reduces D from being calculated for xp to D
    Done by solving quadratic equation iteratively.
    x_1**2 + x1 * (sum' - (A*n**n - 1) * D / (A * n**n)) = D ** (n + 1) / (n ** (2 * n) * prod' * A)
    x_1**2 + b*x_1 = c
    x_1 = (x_1**2 + c) / (2*x_1 + b)
    """
    # x in the input is converted to the same price/precision

    assert i >= 0  # dev: i below zero
    assert i < N_COINS  # dev: i above N_COINS

    c: uint256 = D
    S_: uint256 = 0
    Ann: uint256 = A_ * N_COINS

    _x: uint256 = 0
    for _i in range(N_COINS):
        if _i != i:
            _x = xp[_i]
        else:
            continue
        S_ += _x
        c = c * D / (_x * N_COINS)
    c = c * D / (Ann * N_COINS)
    b: uint256 = S_ + D / Ann
    y_prev: uint256 = 0
    y: uint256 = D
    for _i in range(255):
        y_prev = y
        y = (y*y + c) / (2 * y + b - D)
        # Equality with the precision of 1
        if y > y_prev:
            if y - y_prev <= 1:
                break
        else:
            if y_prev - y <= 1:
                break
    return y


@view
@internal
def _calc_withdraw_one_coin(_token_amount: uint256, i: uint256) -> (uint256, uint256):
    # First, need to calculate
    # * Get current D
    # * Solve Eqn against y_i for D - _token_amount
    amp: uint256 = self._A()
    _fee: uint256 = self.fee * N_COINS / (4 * (N_COINS - 1))
    precisions: uint256[N_COINS] = PRECISION_MUL
    total_supply: uint256 = self.token.totalSupply()

    xp: uint256[N_COINS] = self._xp()

    D0: uint256 = self.get_D(xp, amp)
    D1: uint256 = D0 - _token_amount * D0 / total_supply
    xp_reduced: uint256[N_COINS] = xp

    new_y: uint256 = self.get_y_D(amp, i, xp, D1)
    dy_0: uint256 = (xp[i] - new_y) / precisions[i]  # w/o fees

    for j in range(N_COINS):
        dx_expected: uint256 = 0
        if j == i:
            dx_expected = xp[j] * D1 / D0 - new_y
        else:
            dx_expected = xp[j] - xp[j] * D1 / D0
        xp_reduced[j] -= _fee * dx_expected / FEE_DENOMINATOR

    dy: uint256 = xp_reduced[i] - self.get_y_D(amp, i, xp_reduced, D1)
    dy = (dy - 1) / precisions[i]  # Withdraw less to account for rounding errors

    return dy, dy_0 - dy


@view
@external
def calc_withdraw_one_coin(_token_amount: uint256, i: uint256) -> uint256:
    return self._calc_withdraw_one_coin(_token_amount, i)[0]

@external
@nonreentrant('lock')
def remove_liquidity(_burn_amount: uint256, _min_amounts: uint256[N_COINS]):
    """
    This withdrawal method is very safe, does no complex math
    """
    total_supply: uint256 = self.token.totalSupply()
    amounts: uint256[N_COINS] = empty(uint256[N_COINS])
    amount: uint256 =  _burn_amount - 1 # favor LPs a little bit

    for i in range(N_COINS):
        old_balance: uint256 = self.balances[i]
        value: uint256 = old_balance * amount / total_supply
        assert value >= _min_amounts[i], "Withdrawal resulted in fewer coins than expected"
        self.balances[i] = old_balance - value
        amounts[i] = value
        # sim: comment-out the interaction with coin
        # ----------------------------------------------------------
        # response: Bytes[32] = raw_call(
        #     self.coins[i],
        #     concat(
        #         method_id("transfer(address,uint256)"),
        #         convert(_receiver, bytes32),
        #         convert(value, bytes32),
        #     ),
        #     max_outsize=32,
        # )
        # if len(response) > 0:
        #     assert convert(response, bool)

    total_supply -= _burn_amount
    self.token.burnFrom(msg.sender, _burn_amount)  # dev: insufficient funds

    log RemoveLiquidity(msg.sender, amounts, empty(uint256[N_COINS]), total_supply)

@external
@nonreentrant('lock')
def remove_liquidity_imbalance(
    _amounts: uint256[N_COINS],
    _max_burn_amount: uint256,
) -> uint256:
    """
    Remove an imbalanced amount of coins from the pool.
    """
    amp: uint256 = self._A()
    rates: uint256[N_COINS] = RATES
    old_balances: uint256[N_COINS] = self.balances
    D0: uint256 = self.get_D_mem(old_balances, amp)

    new_balances: uint256[N_COINS] = old_balances
    for i in range(N_COINS):
        amount: uint256 = _amounts[i]
        if amount != 0:
            # print(new_balances[i])
            # print(amount)
            assert new_balances[i] > amount, 'Foo'
            new_balances[i] -= amount
            # sim: comment-out the interaction with coin
            # ----------------------------------------------------------
            # response: Bytes[32] = raw_call(
            #     self.coins[i],
            #     concat(
            #         method_id("transfer(address,uint256)"),
            #         convert(_receiver, bytes32),
            #         convert(amount, bytes32),
            #     ),
            #     max_outsize=32,
            # )
            # if len(response) > 0:
            #     assert convert(response, bool)
    D1: uint256 = self.get_D_mem(new_balances, amp)

    fees: uint256[N_COINS] = empty(uint256[N_COINS])
    base_fee: uint256 = self.fee * N_COINS / (4 * (N_COINS - 1))
    for i in range(N_COINS):
        ideal_balance: uint256 = D1 * old_balances[i] / D0
        difference: uint256 = 0
        new_balance: uint256 = new_balances[i]
        if ideal_balance > new_balance:
            difference = ideal_balance - new_balance
        else:
            difference = new_balance - ideal_balance
        fees[i] = base_fee * difference / FEE_DENOMINATOR
        self.balances[i] = new_balance - (fees[i] * self.admin_fee / FEE_DENOMINATOR)
        new_balances[i] -= fees[i]
    D2: uint256 = self.get_D_mem(new_balances, amp)

    total_supply: uint256 = self.token.totalSupply()
    burn_amount: uint256 = ((D0 - D2) * total_supply / D0) + 1
    assert burn_amount > 1  # dev: zero tokens burned
    assert burn_amount <= _max_burn_amount

    total_supply -= burn_amount
    self.token.burnFrom(msg.sender, burn_amount)  # dev: insufficient funds
    log RemoveLiquidityImbalance(msg.sender, _amounts, fees, D1, total_supply)

    return burn_amount

@external
@nonreentrant('lock')
def remove_liquidity_one_coin(_token_amount: uint256, i: uint256, min_amount: uint256) -> uint256:
    """
    Remove _amount of liquidity all in a form of coin i
    """
    dy: uint256 = 0
    dy_fee: uint256 = 0
    dy, dy_fee = self._calc_withdraw_one_coin(_token_amount, i)
    assert dy >= min_amount, "Not enough coins removed"

    self.balances[i] -= (dy + dy_fee * self.admin_fee / FEE_DENOMINATOR)
    self.token.burnFrom(msg.sender, _token_amount)  # dev: insufficient funds

    # sim: comment-out the interaction with coins.
    # Life is a lot easier for us if we don't bother traversing
    # this code path with mocks and such.
    # ----------------------------------------------------------
    # # "safeTransfer" which works for ERC20s which return bool or not
    # _response: Bytes[32] = raw_call(
    #     self.coins[i],
    #     concat(
    #         method_id("transfer(address,uint256)"),
    #         convert(msg.sender, bytes32),
    #         convert(dy, bytes32),
    #     ),
    #     max_outsize=32,
    # )  # dev: failed transfer
    # if len(_response) > 0:
    #     assert convert(_response, bool)  # dev: failed transfer

    log RemoveLiquidityOne(msg.sender, _token_amount, dy)
    return dy


@view
@external
def A() -> uint256:
    return self._A()


@view
@internal
def _xp() -> uint256[N_COINS]:
    result: uint256[N_COINS] = RATES
    for i in range(N_COINS):
        result[i] = result[i] * self.balances[i] / LENDING_PRECISION
    return result


@pure
@internal
def _xp_mem(_balances: uint256[N_COINS]) -> uint256[N_COINS]:
    result: uint256[N_COINS] = RATES
    for i in range(N_COINS):
        result[i] = result[i] * _balances[i] / PRECISION
    return result


# sim: added function for pool sim testing
@view
@external
def totalSupply() -> uint256:
    return self.token.totalSupply()

