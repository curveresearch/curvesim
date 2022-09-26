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
    D = vyper_3pool.get_D(virtual_balances, A)
    virtual_price = _calc_virtual_price(D, total_supply)

    expected_virtual_price = mainnet_3pool_state["virtual_price"]
    assert virtual_price == expected_virtual_price


def test_get_D(vyper_3pool, mainnet_3pool_state):
    """Test D calculation against vyper implementation."""

    virtual_balances = mainnet_3pool_state["virtual_balances"]
    A = mainnet_3pool_state["A"]
    expected_D = vyper_3pool.get_D(virtual_balances, A)

    balances = mainnet_3pool_state["balances"]
    p = mainnet_3pool_state["p"]
    n_coins = mainnet_3pool_state["N_COINS"]

    pool = Pool(A, D=balances, n=n_coins, p=p)
    D = pool.D()

    assert D == expected_D
