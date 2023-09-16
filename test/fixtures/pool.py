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
    cryptopool.eval(f"self.D={D}")

    virtual_price = 1026434015737186294
    cryptopool.eval(f"self.virtual_price={virtual_price}")

    xcp_profit = 1052829794354693246
    cryptopool.eval(f"self.xcp_profit={xcp_profit}")

    xcp_profit_a = 1052785575319598710
    cryptopool.eval(f"self.xcp_profit_a={xcp_profit_a}")

    last_prices_timestamp = 1689085619
    cryptopool.eval(f"self.last_prices_timestamp={last_prices_timestamp}")

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


def unpack_3_uint64s(packed_nums):
    mask = 2**64 - 1
    return [
        (packed_nums >> 128) & mask,
        (packed_nums >> 64) & mask,
        packed_nums & mask,
    ]


def pack_3_uint64s(nums):
    return (nums[0] << 128) | (nums[1] << 64) | nums[0]


def unpack_prices(packed_prices):
    mask = 2**128 - 1
    return [
        packed_prices & mask,
        (packed_prices >> 128) & mask,
    ]


def pack_prices(prices):
    return (prices[1] << 128) | prices[0]


@pytest.fixture(scope="session")
def _tricrypto_math():
    """
    Initialize vyper fixture for tricrypto_ng's
    external math contract.
    """
    tricrypto_math_filepath = os.path.join(_curve_dir, "tricrypto_math.vy")
    math = boa.load(tricrypto_math_filepath)

    return math


@pytest.fixture(scope="function")
def tricrypto_math(_tricrypto_math):
    """
    Function-scope fixture using titanoboa's snapshotting
    feature to avoid expensive loading.
    """
    with boa.env.anchor():
        yield _tricrypto_math


@pytest.fixture(scope="session")
def _tricrypto_views():
    """
    Initialize vyper fixture for tricrypto_ng's
    external views contract.
    """
    tricrypto_views_filepath = os.path.join(_curve_dir, "tricrypto_views.vy")
    views = boa.load(tricrypto_views_filepath)

    return views


@pytest.fixture(scope="function")
def tricrypto_views(_tricrypto_views):
    """
    Function-scope fixture using titanoboa's snapshotting
    feature to avoid expensive loading.
    """
    with boa.env.anchor():
        yield _tricrypto_views


@pytest.fixture(scope="session")
def _tricrypto_factory(_tricrypto_views, _tricrypto_math):
    """
    Initialize vyper fixture for tricrypto_ng's factory
    contract, which routes select calculations to
    the views and math contracts.
    """
    tricrypto_factory_filepath = os.path.join(_curve_dir, "tricrypto_factory.vy")
    factory = boa.load(tricrypto_factory_filepath, FAKE_ADDRESS, FAKE_ADDRESS)
    factory.eval(f"self.views_implementation = {_tricrypto_views.address}")
    factory.eval(f"self.math_implementation = {_tricrypto_math.address}")

    return factory


@pytest.fixture(scope="function")
def tricrypto_factory(_tricrypto_factory):
    """
    Function-scope fixture using titanoboa's snapshotting
    feature to avoid expensive loading.
    """
    with boa.env.anchor():
        yield _tricrypto_factory


@pytest.fixture(scope="session")
def _vyper_tricrypto(_tricrypto_factory):
    """
    Initialize vyper fixture for crypto pool
    using default volatile pair settings
    """
    trycrypto_ng_filepath = os.path.join(_curve_dir, "tricrypto_ng.vy")
    coins = [FAKE_ADDRESS] * 3

    # settings based on TricryptoUSDT pool
    # https://etherscan.io/address/0xf5f5b97624542d72a9e06f04804bf81baa15e2b4

    A = 1707629
    gamma = 11809167828997
    packed_A_gamma = (A << 128) | gamma
    assert packed_A_gamma == 581076037942835227425498917514114728328226821

    # unpacked_precisioins = [1000000000000, 10000000000, 1]
    packed_precisions = 1000000000000 << 64
    packed_precisions = (packed_precisions | 10000000000) << 64
    packed_precisions = packed_precisions | 1
    assert packed_precisions == 340282366920938463463559074872505306972160000000001

    mid_fee = 3000000
    out_fee = 30000000
    fee_gamma = 500000000000000
    packed_fee_params = mid_fee << 64
    packed_fee_params = (packed_fee_params | out_fee) << 64
    packed_fee_params = packed_fee_params | fee_gamma

    allowed_extra_profit = 2000000000000
    adjustment_step = 490000000000000
    ma_half_time = 865
    packed_rebalancing_params = allowed_extra_profit << 64
    packed_rebalancing_params = (packed_rebalancing_params | adjustment_step) << 64
    packed_rebalancing_params = packed_rebalancing_params | ma_half_time
    assert (
        packed_rebalancing_params == 680564733841876935965653810981216714752000000000865
    )

    # use current price scale as initial prices to match the balances
    # packing is in reverse order
    # 30468634274925745130207
    # 1877445901676407991006
    packed_prices = 1877445901676407991006 << 128
    packed_prices = packed_prices | 30468634274925745130207

    _name = "TricryptoUSDT"
    _symbol = "crvUSDTWBTCWETH"
    _salt = bytes.fromhex(
        "B90B4B3B1043EAF7E27EF307E5FD67AF029117766661203412EDAB9E18E8F6B3"
    )
    _weth = FAKE_ADDRESS
    _math = _tricrypto_factory.math_implementation()

    tricrypto = boa.load(
        trycrypto_ng_filepath,
        _name,
        _symbol,
        coins,
        _math,
        _weth,
        _salt,
        packed_precisions,
        packed_A_gamma,
        packed_fee_params,
        packed_rebalancing_params,
        packed_prices,
    )
    """
    name :
    TricryptoUSDT
    symbol :
    crvUSDTWBTCWETH
    weth :
    0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2
    coins :
    0xdAC17F958D2ee523a2206206994597C13D831ec7
    0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599
    0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2
    math :
    0xcBFf3004a20dBfE2731543AA38599A526e0fD6eE
    salt :
    B90B4B3B1043EAF7E27EF307E5FD67AF029117766661203412EDAB9E18E8F6B3
    packed_precisions :
    340282366920938463463559074872505306972160000000001
    packed_A_gamma :
    581076037942835227425498917514114728328226821
    packed_fee_params :
    1020847100762815390943526144507091182848000000
    packed_rebalancing_params :
    680564733841876935965653810981216714752000000000865
    packed_prices :
    650960167919755280605435624016972588543318000000000000000000
    """

    tricrypto.eval(f"self.factory = {_tricrypto_factory.address}")

    balances = [18418434882428, 60547327748, 9914993293693631287774]
    tricrypto.eval(f"self.balances={balances}")

    D = 55481143937271477730517113
    tricrypto.eval(f"self.D={D}")

    virtual_price = 1000225178597346879
    tricrypto.eval(f"self.virtual_price={virtual_price}")

    xcp_profit = 1000448625854298803
    tricrypto.eval(f"self.xcp_profit={xcp_profit}")

    xcp_profit_a = 1000440033249679801
    tricrypto.eval(f"self.xcp_profit_a={xcp_profit_a}")

    lp_total_supply = 47986553926751950746367
    tricrypto.eval(f"self.totalSupply={lp_total_supply}")

    price_oracle = [30435581307494178154980, 1870286625867949317551]
    price_oracle_packed = pack_prices(price_oracle)
    tricrypto.eval(f"self.price_oracle_packed={price_oracle_packed}")

    last_prices = [30453123431671769818574, 1871140849377954208512]
    last_prices_packed = pack_prices(last_prices)
    tricrypto.eval(f"self.last_prices_packed={last_prices_packed}")

    last_prices_timestamp = 1689085619
    tricrypto.eval(f"self.last_prices_timestamp={last_prices_timestamp}")

    return tricrypto


@pytest.fixture(scope="function")
def vyper_tricrypto(_vyper_tricrypto):
    """
    Function-scope fixture using titanoboa's snapshotting
    feature to avoid expensive loading.
    """
    with boa.env.anchor():
        yield _vyper_tricrypto
