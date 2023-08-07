from pandas import DataFrame
import pytest

from curvesim.pool.sim_interface import (
    SimCurvePool,
    SimCurveRaiPool,
    SimCurveMetaPool,
    SimCurveCryptoPool,
)


@pytest.fixture(scope="function")
def sim_curve_pool():
    return SimCurvePool(A=250, D=1000000 * 10**18, n=2, admin_fee=5 * 10**9)


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
