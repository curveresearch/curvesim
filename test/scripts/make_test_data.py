import os
import pickle
import shutil
from itertools import combinations

import curvesim
from curvesim.network.nomics import coin_ids_from_addresses_sync

pipeline = curvesim.pipelines.arbitrage.volume_limited_arbitrage
data_dir = os.path.join("data")
test_data_dir = os.path.join("test", "data")
pool_names = ["3CRV", "a3CRV", "FRAX3CRV-f", "MIM-3LP3CRV-f", "RAI3CRV"]

# Store the data
print("Getting pool/price data...")
for pool in pool_names:
    pool_data = curvesim.pool_data.get(pool)

    # Store pool_data
    pool_data.set_cache()
    f_name = os.path.join(test_data_dir, pool + "-pool_data.pickle")
    with open(f_name, "wb") as f:
        pickle.dump(pool_data, f)

    # Store price data
    coins = pool_data.coins()
    curvesim.price_data.get(coins, src="nomics")

    # Copy price files to test/data
    coin_combos = list(combinations(coins, 2))
    for i, pair in enumerate(coin_combos):
        id_pair = coin_ids_from_addresses_sync(pair)
        f_from = os.path.join(data_dir, f"{id_pair[0]}-{id_pair[1]}.csv")
        f_to = os.path.join(test_data_dir, f"{pair[0]}-{pair[1]}.csv")
        shutil.copyfile(f_from, f_to)


# Run sim from stored data and save results
print("Getting sim results...")
for pool in pool_names:
    f_name = os.path.join(test_data_dir, pool + "-pool_data.pickle")
    with open(f_name, "rb") as f:
        pool_data = pickle.load(f)

    results = pipeline(pool_data, test=True, src="local", data_dir=test_data_dir)

    f_name = os.path.join(test_data_dir, pool + "-results.pickle")
    with open(f_name, "wb") as f:
        pickle.dump(results, f)
