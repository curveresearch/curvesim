"""
Test the entire sim pipeline, starting with canned data.

Technically these are not end-to-end tests since we don't pull the data,
so besides the network code there is a lack of coverage around the
`pool_data` and `price_data` packages.
"""
import os
import pickle

import numpy as np

import curvesim

if __name__ == "__main__":  # noqa: C901
    data_dir = os.path.join("test", "data")
    pool_names = [
        "0xbebc44782c7db0a1a60cb6fe97d0b483032ff1c7",
        "0xdebf20617708857ebe4f679508e7b7863a8a8eee",  # aCRV
        "FRAX3CRV-f",
        "MIM-3LP3CRV-f",
        # "0x618788357d0ebd8a37e763adab3bc575d54c2c7d",  # RAI3CRV
    ]

    abs_tolerances = {
        "ar": 1.5e-4,
        "bal": 0.035,
        "depth": 10,  # in liquidity density units
        "err": 0.01,
        "log_returns": 0,
        "p": 1e15,
        "pool_value": 0,  # in dollar units
        "volume": 0,
        "x": 0,
    }

    rel_tolerances = {"pool_value": 0.0001}

    skipped = ["log_returns", "volume", "x"]

    for pool_name in pool_names:
        with open(os.path.join(data_dir, f"{pool_name}-pool_data.pickle"), "rb") as f:
            pool_data = pickle.load(f)

        res = curvesim.autosim(
            pool_name,
            test=True,
            ncpu=4,
            src="local",
            data_dir=data_dir,
            pool_data=pool_data,
        )
        # with open(os.path.join(data_dir, f"{pool_name}-res-test.pickle"), "rb") as f:
        #     res = pickle.load(f)

        with open(os.path.join(data_dir, f"{pool_name}-results.pickle"), "rb") as f:
            res_pkl = pickle.load(f)

        for (key, df1) in res.items():
            if key in skipped:
                continue
            df2 = res_pkl[key]
            if len(df1) != len(df2):
                raise AssertionError(f"Different dataframe lengths for key: {key}")

            atol = abs_tolerances.get(key, 0)
            rtol = rel_tolerances.get(key, 0)

            if key not in ["p", "x"]:
                for i in df1:
                    if len(df1[i]) != len(df2[i]):
                        raise AssertionError(f"Different row lengths for row: {i}")
                    mismatch_indices = np.where(
                        ~np.isclose(df1[i], df2[i], atol=atol, rtol=rtol)
                    )[0]
                    if len(mismatch_indices) > 0:  # numpy arrays are funny
                        print(f"Mismatch in {key}, {i}")
                        for j in mismatch_indices:
                            array1 = np.array(df1[i])
                            array2 = np.array(df2[i])
                            print(
                                "Diff:",
                                abs(array1[j] - array2[j]),
                                array1[j],
                                array2[j],
                            )
                        raise AssertionError(f"Mismatch in {key}, {i}")
            else:
                for i in df1:
                    if len(df1[i]) != len(df2[i]):
                        raise AssertionError(f"Different row lengths for row: {i}")
                    for (array1, array2) in zip(df1[i], df2[i]):
                        array1 = np.array(array1, dtype=float)
                        array2 = np.array(array2, dtype=float)
                        if len(array1) != len(array2):
                            raise AssertionError(
                                f"Different array lengths for row: {i}"
                            )
                        mismatch_indices = np.where(
                            ~np.isclose(array1, array2, atol=atol, rtol=rtol)
                        )[0]
                        if len(mismatch_indices) > 0:  # numpy arrays are funny
                            print(f"Mismatch in {key}, {i}")
                            for j in mismatch_indices:
                                print(
                                    "Diff:",
                                    abs(array1[j] - array2[j]),
                                    array1[j],
                                    array2[j],
                                )
                            raise AssertionError(f"Mismatch in {key}, {i}")
