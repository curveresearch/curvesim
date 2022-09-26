import os

import boa
import pytest

_base_dir = os.path.dirname(__file__)


@pytest.fixture(scope="function")
def vyper_3pool():
    print(_base_dir)
    filepath = os.path.join(_base_dir, "fixtures", "calcs_for_3pool.vy")
    return boa.load(filepath)


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
