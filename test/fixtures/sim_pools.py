import pytest
from pandas import DataFrame

from curvesim.pool.sim_interface import (
    SimCurveCryptoPool,
    SimCurveMetaPool,
    SimCurvePool,
    SimCurveRaiPool,
)


@pytest.fixture(scope="function")
def sim_curve_pool():
    return SimCurvePool(A=250, D=1000000 * 10**18, n=2, admin_fee=5 * 10**9)


@pytest.fixture(scope="function")
def sim_curve_tripool():
    return SimCurvePool(A=250, D=1000000 * 10**18, n=3, admin_fee=5 * 10**9)


@pytest.fixture(scope="function")
def sim_curve_meta_pool():
    basepool = SimCurvePool(A=250, D=1000000 * 10**18, n=2, admin_fee=5 * 10**9)

    kwargs = {
        "A": 250,
        "D": 4000000 * 10**18,
        "n": 2,
        "admin_fee": 5 * 10**9,
        "basepool": basepool,
    }

    return SimCurveMetaPool(**kwargs)


@pytest.fixture(scope="function")
def sim_curve_rai_pool():
    basepool = SimCurvePool(A=250, D=1000000 * 10**18, n=2, admin_fee=5 * 10**9)

    kwargs = {
        "A": 250,
        "D": 4000000 * 10**18,
        "n": 2,
        "admin_fee": 5 * 10**9,
        "basepool": basepool,
        "redemption_prices": DataFrame([1, 2, 3], columns=["price"]),
    }

    return SimCurveRaiPool(**kwargs)


@pytest.fixture(scope="function")
def sim_curve_crypto_pool():
    kwargs = {
        "A": 400000,
        "gamma": 72500000000000,
        "n": 2,
        "precisions": [1, 1],
        "mid_fee": 26000000,
        "out_fee": 45000000,
        "allowed_extra_profit": 2000000000000,
        "fee_gamma": 230000000000000,
        "adjustment_step": 146000000000000,
        "admin_fee": 5000000000,
        "ma_half_time": 600,
        "price_scale": [1550997347493624157],
        "balances": [20477317313816545807568241, 13270936465339000000000000],
        "tokens": 1550997347493624157,
        "xcp_profit": 1052829794354693246,
        "xcp_profit_a": 1052785575319598710,
    }

    return SimCurveCryptoPool(**kwargs)


@pytest.fixture(scope="function")
def sim_curve_tricrypto_pool():
    kwargs = {
        "A": 1707629,
        "gamma": 11809167828997,
        "n": 3,
        "precisions": [1, 1, 1],
        "mid_fee": 3000000,
        "out_fee": 30000000,
        "allowed_extra_profit": 2000000000000,
        "fee_gamma": 500000000000000,
        "adjustment_step": 490000000000000,
        "admin_fee": 5000000000,
        "ma_half_time": 865,
        "price_scale": [30453123431671769818574, 1871140849377954208512],
        "balances": [
            18418434882428000000000000,
            605473277480000000000,
            9914993293693631287774,
        ],
        "tokens": 47986553926751950746367,
        "xcp_profit": 1000448625854298803,
        "xcp_profit_a": 1000440033249679801,
    }

    return SimCurveCryptoPool(**kwargs)
