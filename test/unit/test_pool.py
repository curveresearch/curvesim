import boa


def test_get_D():

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
