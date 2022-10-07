import os

import boa
import pytest

_base_dir = os.path.dirname(__file__)
FAKE_ADDRESS = "0xCAFECAFECAFECAFECAFECAFECAFECAFECAFECAFE"


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


@pytest.fixture(scope="session")
def _vyper_3pool(mainnet_3pool_state):
    """Initialize vyper fixture using mainnet values."""
    lp_total_supply = mainnet_3pool_state["lp_tokens"]
    mock_filepath = os.path.join(_base_dir, "lp_token_mock.vy")
    lp_token = boa.load(mock_filepath, lp_total_supply)

    pool_filepath = os.path.join(_base_dir, "basepool.vy")
    owner = FAKE_ADDRESS
    coins = [FAKE_ADDRESS] * 3
    A = mainnet_3pool_state["A"]
    fee = 4 * 10**6
    admin_fee = 5 * 10**9
    pool = boa.load(pool_filepath, owner, coins, lp_token, A, fee, admin_fee)

    balances = mainnet_3pool_state["balances"]
    pool.eval(f"self.balances={balances}")

    return pool


@pytest.fixture(scope="session")
def _vyper_metapool(_vyper_3pool):
    """Initialize vyper fixture using mainnet values."""
    metapool_filepath = os.path.join(_base_dir, "metapool.vy")
    name = "SIM-3Pool"
    symbol = "SIM3CRV-f"
    coin = FAKE_ADDRESS
    rate_multiplier = 10**34  # 2 decimals
    basepool = _vyper_3pool.address
    basepool_token = _vyper_3pool.token()
    A = 1000
    fee = 4 * 10**6
    # Admin fee is hard-coded as 50% for factory pools
    # admin_fee = 5 * 10**9
    metapool = boa.load(
        metapool_filepath,
        name,
        symbol,
        coin,
        basepool,
        basepool_token,
        rate_multiplier,
        A,
        fee,
    )

    balances = [762951074, 12971664836474542835562756]
    metapool.eval(f"self.balances={balances}")
    total_supply = 20312687702458911532611097
    metapool.eval(f"self.totalSupply={total_supply}")

    return metapool


@pytest.fixture(scope="function")
def vyper_3pool(_vyper_3pool):
    with boa.env.anchor():
        yield _vyper_3pool


@pytest.fixture(scope="function")
def vyper_metapool(_vyper_metapool):
    with boa.env.anchor():
        yield _vyper_metapool
