"""Pool fixtures to test against vyper implementation.  Uses titanoboa."""
# pylint: disable=redefined-outer-name
import os

import boa
import pytest

_base_dir = os.path.dirname(__file__)
_curve_dir = os.path.join(_base_dir, "curve")
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

    pool_filepath = os.path.join(_curve_dir, "basepool.vy")
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
    metapool_filepath = os.path.join(_curve_dir, "metapool.vy")
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


@pytest.fixture(scope="session")
def _cryptopool_lp_token():
    lp_total_supply = 16060447504694332256465310
    mock_filepath = os.path.join(_base_dir, "lp_token_mock.vy")
    lp_token = boa.load(mock_filepath, lp_total_supply)
    return lp_token


@pytest.fixture(scope="session")
def _vyper_cryptopool(_cryptopool_lp_token):
    """
    Initialize vyper fixture for crypto pool
    using default volatile pair settings
    """
    cryptopool_filepath = os.path.join(_curve_dir, "cryptopool.vy")
    coins = [FAKE_ADDRESS] * 2

    # settings based on STG/USDC pool
    # https://etherscan.io/address/0x3211c6cbef1429da3d0d58494938299c92ad5860

    # lp_total_supply = 16060447504694332256465310
    # mock_filepath = os.path.join(_base_dir, "lp_token_mock.vy")
    # lp_token = boa.load(mock_filepath, lp_total_supply)

    A = 400000
    gamma = 72500000000000
    # unpacked_precisions = [10**0, 10**12]
    precisions = 12 << 8
    precisions = precisions | 0  # for explicitness
    mid_fee = 26000000
    out_fee = 45000000
    allowed_extra_profit = 2000000000000
    fee_gamma = 230000000000000
    adjustment_step = 146000000000000
    admin_fee = 5000000000
    ma_half_time = 600
    initial_price = 1550997347493624157

    cryptopool = boa.load(
        cryptopool_filepath,
        A,
        gamma,
        mid_fee,
        out_fee,
        allowed_extra_profit,
        fee_gamma,
        adjustment_step,
        admin_fee,
        ma_half_time,
        initial_price,
        _cryptopool_lp_token,
        coins,
        precisions,
    )

    balances = [20477317313816545807568241, 13270936465339]
    cryptopool.eval(f"self.balances={balances}")
    D = 41060496962103963853877954
    virtual_price = 1026434015737186294
    cryptopool.eval(f"self.D={D}")
    cryptopool.eval(f"self.virtual_price={virtual_price}")
    xcp_profit = 1052829794354693246
    xcp_profit_a = 1052785575319598710
    cryptopool.eval(f"self.xcp_profit={xcp_profit}")
    cryptopool.eval(f"self.xcp_profit_a={xcp_profit_a}")

    return cryptopool


@pytest.fixture(scope="function")
def vyper_3pool(_vyper_3pool):
    """
    Function-scope fixture using titanoboa's snapshotting
    feature to avoid expensive loading.
    """
    with boa.env.anchor():
        yield _vyper_3pool


@pytest.fixture(scope="function")
def vyper_metapool(_vyper_metapool):
    """
    Function-scope fixture using titanoboa's snapshotting
    feature to avoid expensive loading.
    """
    with boa.env.anchor():
        yield _vyper_metapool


@pytest.fixture(scope="function")
def cryptopool_lp_token(_cryptopool_lp_token):
    """
    Function-scope fixture using titanoboa's snapshotting
    feature to avoid expensive loading.
    """
    with boa.env.anchor():
        yield _cryptopool_lp_token


@pytest.fixture(scope="function")
def vyper_cryptopool(_vyper_cryptopool):
    """
    Function-scope fixture using titanoboa's snapshotting
    feature to avoid expensive loading.
    """
    with boa.env.anchor():
        yield _vyper_cryptopool
