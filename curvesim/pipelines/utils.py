from math import factorial

from numpy import append


# Volume Multipliers
def compute_volume_multipliers(pool_vol, market_vol, n, pool_type, mode=1):
    if pool_type == "Pool":
        vol_mult = pool_vol_mult(pool_vol, market_vol, n, mode)

    elif pool_type == "MetaPool":
        vol_mult = metapool_vol_mult(pool_vol, market_vol, n, mode)

    else:
        raise TypeError(f"Pool type {pool_type} not supported by this pipeline")

    print("Volume Multipliers:")
    print(vol_mult)

    return vol_mult


def pool_vol_mult(pool_vol, market_vol, n, mode):
    if mode == 1:
        vol_mult = pool_vol / market_vol.sum()

    if mode == 2:
        vol_mult = pool_vol.repeat(n) / n / market_vol

    if mode == 3:
        print("Vol_mode=3 only available for meta-pools. Reverting to vol_mode=1")
        vol_mult = pool_vol / market_vol.sum()

    return vol_mult


def metapool_vol_mult(pool_vol, market_vol, n, mode):
    pool_vol_meta = pool_vol[0]
    pool_vol_base = pool_vol[1]
    mkt_vol_meta = market_vol[0 : n[1]]
    mkt_vol_base = market_vol[n[1] :]

    n_base_pairs = int(factorial(n[1]) / 2 * factorial(n[1] - 2))

    if mode == 1:
        vol_mult = append(
            pool_vol_meta / mkt_vol_meta.sum().repeat(n[1]),
            pool_vol_base / mkt_vol_base.sum().repeat(n_base_pairs),
        )

    elif mode == 2:
        vol_mult = append(
            pool_vol_meta.repeat(n[1]) / n[1] / mkt_vol_meta,
            pool_vol_base.repeat(n_base_pairs) / n_base_pairs / mkt_vol_base,
        )

    elif mode == 3:
        vol_mult = append(
            pool_vol_meta.repeat(n[1]) / n[1] / mkt_vol_meta,
            pool_vol_base / mkt_vol_base.sum().repeat(n_base_pairs),
        )

    return vol_mult
