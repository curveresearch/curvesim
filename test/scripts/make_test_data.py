"""Script to generate data for CI test"""
import os
import pickle
import shutil
from itertools import combinations

import curvesim
from curvesim.network.nomics import coin_ids_from_addresses_sync
from curvesim.pipelines.arbitrage import volume_limited_arbitrage as pipeline


def main():
    """
    Script starts a multiprocessing pool so needs to be wrapped in a
    function to avoid recursively importing and creating sub-processes,
    cf subsection "Safe importing of main module" of
    https://docs.python.org/3/library/multiprocessing.html#multiprocessing-programming
    """
    test_data_dir = os.path.join("test", "data")
    pools = [
        # 3CRV
        {
            "address": "0xbebc44782c7db0a1a60cb6fe97d0b483032ff1c7",
            "end_timestamp": 1638316800,
        },
        # aCRV
        {
            "address": "0xdebf20617708857ebe4f679508e7b7863a8a8eee",
            "end_timestamp": 1622505600,
        },
        # frax3CRV"
        {
            "address": "FRAX3CRV-f",
            "end_timestamp": 1643673600,
        },
        # mim3CRV
        {
            "address": "MIM-3LP3CRV-f",
            "end_timestamp": 1646265600,
        },
        # rai3CRV
        {
            "address": "0x618788357d0ebd8a37e763adab3bc575d54c2c7d",
            "end_timestamp": 1654041600,
        },
    ]

    # Store the data
    print("Getting pool/price data...")
    for pool in pools:
        address = pool["address"]
        end_ts = pool["end_timestamp"]

        pool_data = curvesim.pool_data.get(address)

        # Store pool_data
        pool_data.set_cache(end=end_ts)
        f_name = os.path.join(test_data_dir, address + "-pool_data.pickle")
        with open(f_name, "wb") as f:
            pickle.dump(pool_data, f)

        # Store price data
        coins = pool_data.coins
        curvesim.price_data.get(coins, src="nomics", data_dir=test_data_dir, end=end_ts)

        # Rename files from coin IDs to addresses.
        # Need to do this because the sim pipeline actually uses the addresses.
        # FIXME: update the nomics file download to use addresses.
        coin_combos = combinations(coins, 2)
        for pair in coin_combos:
            id_pair = coin_ids_from_addresses_sync(pair)
            f_from = os.path.join(
                test_data_dir, f"{id_pair[0]}-{id_pair[1]}-{end_ts}.csv"
            )
            f_to = os.path.join(test_data_dir, f"{pair[0]}-{pair[1]}-{end_ts}.csv")
            shutil.copyfile(f_from, f_to)

    # Run sim from stored data and save results
    print("Getting sim results...")
    for pool in pools:
        address = pool["address"]
        end_ts = pool["end_timestamp"]
        vol_mult = pool.get("vol_mult", None)

        f_name = os.path.join(test_data_dir, address + "-pool_data.pickle")
        with open(f_name, "rb") as f:
            pool_data = pickle.load(f)

        results = pipeline(
            pool_data,
            test=True,
            src="local",
            data_dir=test_data_dir,
            end=end_ts,
            vol_mult=vol_mult,
        )

        f_name = os.path.join(test_data_dir, address + "-results.pickle")
        with open(f_name, "wb") as f:
            pickle.dump(results, f)


if __name__ == "__main__":
    main()
