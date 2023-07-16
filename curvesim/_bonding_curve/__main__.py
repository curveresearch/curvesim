import curvesim

from . import bonding_curve

pool_address = "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"
pool = curvesim.pool.get(pool_address)
pair_to_curve = bonding_curve(pool)
