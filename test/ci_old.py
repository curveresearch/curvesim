import os
import pickle

import numpy as np

import curvesim

if __name__ == "__main__":  # noqa: C901
    data_dir = os.path.join("test", "data")
    pool_names = [
        ("3pool", "3crv"),
        ("aave", "a3CRV"),
        ("frax", "FRAX3CRV-f"),
        ("mim", "MIM-3LP3CRV-f "),
    ]

    abs_tolerances = {
        "ar": 1.5e-4,
        "bal": 0.035,
        "depth": 0.02,
        "err": 0.01,
        "log_returns": 0,
        "p": 1e15,
        "pool_value": 50000,
        "volume": 0,
        "x": 0,
    }
    rel_tolerances = {}

    skipped = ["log_returns", "volume", "x"]

    for pool_name in pool_names:
        with open(os.path.join(data_dir, f"{pool_name[0]}-pooldata.pickle"), "rb") as f:
            pool_data = pickle.load(f)

        res = curvesim.autosim(
            pool_name[1],
            test=True,
            ncpu=4,
            src="local",
            data_dir=data_dir,
            pool_data=pool_data,
        )
        # with open(os.path.join(data_dir, f"{pool_name}-res-test.pickle"), "rb") as f:
        #     res = pickle.load(f)

        with open(os.path.join(data_dir, f"{pool_name[0]}-res.pickle"), "rb") as f:
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
