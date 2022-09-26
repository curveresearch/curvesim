from curvesim.pool import Pool


def _calc_virtual_price(D, total_supply):
    return D * 10**18 // total_supply


def test_get_D_against_prod(vyper_3pool, mainnet_3pool_state):
    """Test boa value against live contract."""

    virtual_balances = mainnet_3pool_state["virtual_balances"]
    A = mainnet_3pool_state["A"]
    total_supply = mainnet_3pool_state["lp_tokens"]

    # Compare against virtual price since that's exposed externally
    # while `get_D` is internal in the contract.
    D = vyper_3pool.D(virtual_balances, A)
    virtual_price = _calc_virtual_price(D, total_supply)

    expected_virtual_price = mainnet_3pool_state["virtual_price"]
    assert virtual_price == expected_virtual_price


def test_get_D(vyper_3pool, mainnet_3pool_state):
    """Test D calculation against vyper implementation."""

    virtual_balances = mainnet_3pool_state["virtual_balances"]
    A = mainnet_3pool_state["A"]
    expected_D = vyper_3pool.D(virtual_balances, A)

    balances = mainnet_3pool_state["balances"]
    p = mainnet_3pool_state["p"]
    n_coins = mainnet_3pool_state["N_COINS"]

    pool = Pool(A, D=balances, n=n_coins, p=p)
    D = pool.D()

    assert D == expected_D


def test_get_D_balanced():
    """Sanity check for when pool is perfectly balanced"""

    # create balanced pool
    balances = [
        295949605740077000000000000,
        295949605740077,
        295949605740077,
    ]
    p = [10**18, 10**30, 10**30]
    n_coins = 3
    A = 5858

    pool = Pool(A, D=balances, n=n_coins, p=p)
    D = pool.D()

    virtualized_balances = [b * p // 10**18 for b, p in zip(balances, p)]
    expected_D = sum(virtualized_balances)

    assert D == expected_D


def test_get_y(vyper_3pool, mainnet_3pool_state):
    """Test y calculation against vyper implementation"""
    virtual_balances = mainnet_3pool_state["virtual_balances"]
    balances = mainnet_3pool_state["balances"]
    n_coins = mainnet_3pool_state["N_COINS"]
    A = mainnet_3pool_state["A"]
    p = mainnet_3pool_state["p"]
    pool = Pool(A, D=balances, n=n_coins, p=p)

    i = 0
    j = 1
    x = 516 * 10**18
    expected_y = vyper_3pool.y(i, j, x, virtual_balances)

    y = pool.y(i, j, x, virtual_balances)
    assert y == expected_y
