import curvesim
from curvesim import bonding_curve


def test_bonding_curve_stableswap():
    """Simple test of the bonding curve for a regular stableswap."""
    A = 2000
    balances = [96930673769101734848937206, 96029665968769, 94203880672841]
    rates = [10**18, 10**30, 10**30]
    pool = curvesim.pool.make(A, balances, 3, rates=rates)
    pair_to_curve = bonding_curve(pool, resolution=5)
    expected_result = {
        (0, 1): [
            (143582.10515040305, 207709896.10151905),
            (52035160.60424256, 140938067.54743478),
            (103926739.10333471, 89033886.31117772),
            (155818317.6024269, 37171084.50615266),
            (207709896.10151905, 143582.1051504031),
        ],
        (0, 2): [
            (143582.10515040305, 205740351.86334246),
            (51542774.54469842, 139604657.24397892),
            (102941966.98424643, 88192864.27513982),
            (154341159.42379445, 36822438.40404793),
            (205740351.86334246, 143582.10515040308),
        ],
        (1, 2): [
            (143582.10515040305, 204771181.49157524),
            (51300481.95175662, 138945948.269023),
            (102457381.79836284, 87776447.07614492),
            (153614281.64496905, 36648317.74309717),
            (204771181.49157527, 143582.10515040296),
        ],
    }
    assert pair_to_curve == expected_result


def test_bonding_curve_metapool():
    """Simple test of the bonding curve for a regular stableswap.

    Note: test data was generated via

        pool_address = "0x4e43151b78b5fbb16298C1161fcbF7531d5F8D93"
        pool = curvesim.pool.get(pool_address)
        basepool = pool.basepool
        pair_to_curve = bonding_curve(pool, resolution=5)
    """
    pool_address = "0x4e43151b78b5fbb16298C1161fcbF7531d5F8D93"
    pool = curvesim.pool.get(pool_address)
    basepool = pool.basepool
    pair_to_curve = bonding_curve(pool, resolution=5)

    A = 1500
    rates = [10**18, 10**30]
    balances = [350744085115649212803306457, 141003714500628]
    bp_tokens = 491124709934878945923137105
    basepool = curvesim.pool.make(A, balances, 2, rates=rates, tokens=bp_tokens)

    A = 1500
    balances = [7059917, 88935085280709722288137]
    rate_multiplier = 10**34
    pool = curvesim.pool.make(
        A,
        balances,
        2,
        rate_multiplier=rate_multiplier,
        basepool=basepool,
    )
    pair_to_curve = bonding_curve(pool, resolution=5)
    expected_result = {
        (0, 1): [
            (79.81988656375063, 182748.88552045962),
            (45747.08629503773, 113904.53710112568),
            (91414.35270351169, 68226.56650379577),
            (137081.61911198567, 22614.30606286462),
            (182748.88552045965, 79.81988656375057),
        ]
    }

    assert pair_to_curve == expected_result


def test_bonding_curve_cryptoswap():
    """
    Simple test of the bonding curve for a regular cryptoswap.

    Parameters taken from 0xd51a44d3fae010294c616388b506acda1bfaae46
    (Tricrypto-2 pool) on Oct. 10, 2023, ~4 PM EDT.
    """
    A = 1707629
    gamma = 11809167828997
    n = 3
    precisions = [1000000000000, 10000000000, 1]
    mid_fee = 3000000
    out_fee = 30000000
    allowed_extra_profit = 2000000000000
    fee_gamma = 500000000000000
    adjustment_step = 490000000000000
    ma_half_time = 600
    price_scale = [27823549548207248490238, 1580164282540758832038]
    balances = [21282026780687, 77735630688, 13482330187707402680192]
    D = 64214523455757010937592598

    pool = curvesim.pool.CurveCryptoPool(
        A,
        gamma,
        n,
        precisions,
        mid_fee,
        out_fee,
        allowed_extra_profit,
        fee_gamma,
        adjustment_step,
        ma_half_time,
        price_scale,
        balances=balances,
        D=D,
    )

    pair_to_curve = bonding_curve(pool, resolution=5)

    expected_result = {
        (0, 1): [
            (64214523.455757014, 257.0830793764587),
            (49949133.541076906, 330.62933900193525),
            (35683743.626396805, 463.0556701281358),
            (21418353.711716697, 772.4361029340506),
            (7152963.7970365975, 2307.919891547214),
        ],
        (0, 2): [
            (64214523.455757014, 4458.778590637992),
            (49922293.25998866, 5737.424624762623),
            (35630063.064220294, 8043.1971137980945),
            (21337832.868451938, 13447.046511020473),
            (7045602.672683579, 40637.87807714902),
        ],
        (1, 2): [
            (2307.9198915472143, 4531.460155851949),
            (1795.2779668453447, 5827.600890376516),
            (1282.6360421434752, 8161.168801564149),
            (769.9941174416056, 13611.631993297762),
            (257.3521927397361, 40637.87807714902),
        ],
    }

    assert pair_to_curve == expected_result
