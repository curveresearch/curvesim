import boa

from curvesim.pool import Pool


def test_get_D_against_prod():
    """Test boa value against live contract."""

    vyper_pool = boa.load("test/unit/pool_calcs.vy")
    A = 2000
    balances = [
        295949605740077243186725223,
        284320067518878 * 10**12,
        288200854907854 * 10**12,
    ]
    D = vyper_pool.get_D(balances, A)
    total_supply = 849743149250065202008212976
    virtual_price = D * 10**18 // total_supply

    # Compare against virtual price since that's exposed externally
    # while `get_D` is internal in the contract.
    expected_virtual_price = 1022038799187029697
    assert virtual_price == expected_virtual_price


def test_get_D():
    """Test D calculation against vyper implementation."""

    vyper_pool = boa.load("test/unit/pool_calcs.vy")
    A = 2000
    balances = [
        295949605740077243186725223,
        284320067518878,
        288200854907854,
    ]
    virtual_balances = [balances[0], balances[1] * 10**12, balances[2] * 10**12]
    expected_D = vyper_pool.get_D(virtual_balances, A)
    pool = Pool(A, D=balances, n=3, p=[10**18, 10**30, 10**30])
    D = pool.D()
    assert D == expected_D
