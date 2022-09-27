import os

import boa
import pytest

_base_dir = os.path.dirname(__file__)


@pytest.fixture(scope="session")
def mainnet_3pool_state():
    """Snapshot of Mainnet 3Pool values"""
    p = [10**18, 10**30, 10**30]
    balances = [
        295949605740077243186725223,
        284320067518878,
        288200854907854,
    ]
    virtual_balances = [b * p // 10**18 for b, p in zip(balances, p)]

    return {
        "N_COINS": 3,
        "A": 2000,
        "p": p,
        "balances": balances,
        "virtual_balances": virtual_balances,
        "lp_tokens": 849743149250065202008212976,
        "virtual_price": 1022038799187029697,
    }


@pytest.fixture(scope="function")
def vyper_3pool(mainnet_3pool_state):
    erc20_filepath = os.path.join(_base_dir, "fixtures", "erc20_mock.vy")
    lp_total_supply = mainnet_3pool_state["lp_tokens"]
    lp_token = boa.load(erc20_filepath, "Mock 3CRV", "MOCK-3CRV", 18, lp_total_supply)

    pool_filepath = os.path.join(_base_dir, "fixtures", "calcs_for_3pool.vy")
    owner = "0xCAFECAFECAFECAFECAFECAFECAFECAFECAFECAFE"
    dai_mock = boa.load(erc20_filepath, "Mock DAI", "MOCK-DAI", 18, 10**26).address
    usdc_mock = boa.load(erc20_filepath, "Mock USDC", "MOCK-USDC", 6, 10**26).address
    tether_mock = boa.load(erc20_filepath, "Mock Tether", "MOCK-UST", 6, 10**26).address
    coins = [dai_mock, usdc_mock, tether_mock]
    A = mainnet_3pool_state["A"]
    fee = 4 * 10**6
    admin_fee = fee // 2
    pool = boa.load(pool_filepath, owner, coins, lp_token, A, fee, admin_fee)

    balances = mainnet_3pool_state["balances"]
    pool.eval(f"self.balances={balances}")

    return pool
